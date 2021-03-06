from django.shortcuts import render
from django.http import HttpResponse
from mysite.settings import AWS_ACCESS_KEY, AWS_SECRET_KEY, BUCKET_NAME, REGION_NAME
import boto3
from boto3.session import Session
from django.shortcuts import redirect
import pymysql
from datetime import datetime
import os
from django.views.decorators.csrf import csrf_exempt
from home.utils.token import check_token, set_cookie 
from home.utils.db import init_db, select_one, select_all, insert
from home.models import User
import json
import webbrowser
import mysite.settings

### 회원가입하면 그 유저 아이디로 파일 경로 한개 만들어줘야댐.

def index(request):
    if check_token(request):
        return render(request, 'index.html', {'user_email' : request.COOKIES.get('khustagram_login')})
    else:
        return render(request, 'login.html')

@csrf_exempt
def signup(request):
    try:
        data=json.loads(request.body.decode("utf-8"))
    except ValueError:
        return "Input must be json format", 400

    user = User.create_from_request(data)

    query = "select * from khu_user where user_email = '%s'"
    user_db = select_one(query % user.user_email)

    if user_db is not None:
        return HttpResponse("User is already existed")
    query = "insert into khu_user (usr_name, user_email, user_pw) values ('%s', '%s', '%s')"
    insert(query % (user.usr_name, user.user_email, user.user_pw))
    session = boto3.session.Session(aws_access_key_id = AWS_ACCESS_KEY, aws_secret_access_key = AWS_SECRET_KEY, region_name = REGION_NAME)
    s3 = session.resource('s3')
    s3.Bucket(BUCKET_NAME).put_object(Key = user.user_email+"/", Body = "")
    print(user.user_email + "is sign up")
    return HttpResponse("Signup Success")
    
@csrf_exempt
def signin(request):
    try:
        data=json.loads(request.body.decode("utf-8"))
    except ValueError:
        return "Input must be json format", 400

    user = User.create_from_request(data)

    query = "select * from khu_user where user_email = '%s'"
    user_db=select_one(query % user.user_email)

    if user_db is None:
        return HttpResponse("User not existed")

    if user_db[3] != user.user_pw:
        return HttpResponse("Incorrect password")

    response = HttpResponse('set cookie')
    response.set_cookie('khustagram_login',user_db[1])
    return response

def upload(request):
    if request.method =='GET':
        return render(request, 'index.html')#그 직전 경로로 이동하게 수정
    if request.method =='POST':
    
        user_email = request.COOKIES.get('khustagram_login')
        #애초에 localhost/files/일때만 업로드 가능하게
        #현재 url 받기
        cur_url = request.POST.get('cur_url')
        print(cur_url)
        cururls = cur_url.split('/')
        print (cururls)
        #rladnjsrb9999에 현재 세션의 유저아이디 들어가야댐.
        parsed_url=''
        for index in range(0,len(cururls)):
            if index > 4:
                parsed_url+='/'+cururls[index]

        print(parsed_url)

        #POST FILE
        fileToUPLOAD = request.FILES.get('fileToUPLOAD')
        filepath = user_email+parsed_url
        cloudFilename = filepath+fileToUPLOAD.name
        #이전 경로
        pre_url = filepath

        #S3에 추가
        session = boto3.session.Session(aws_access_key_id = AWS_ACCESS_KEY,
                                        aws_secret_access_key = AWS_SECRET_KEY,
                                        region_name = REGION_NAME)
        s3 = session.resource('s3')
        s3.Bucket(BUCKET_NAME).put_object(Key = cloudFilename, Body =fileToUPLOAD)

        #file table에 추가
        db = pymysql.connect(host='localhost', user='root',passwd='hshadow189', db='khustagram', port=3306)
        cursor = db.cursor()

        #현재 파일 경로와 넣으려는 파일 이름을 넣기
        check_sql ="""select filename from file_table WHERE filepath=%s
        AND filename = %s
        """
        #있으면 1반환

        isFiles = cursor.execute(check_sql,(filepath,fileToUPLOAD.name))
        print(isFiles)
        if isFiles == 1:
            sql = """ update file_table SET ts=%s WHERE filepath=%s AND filename=%s
                    """

            cursor.execute(sql,(datetime.now(),filepath,fileToUPLOAD.name))
            db.commit()
            cursor.close()

            return redirect('/files/'+pre_url)#그 직전 경로로 이동하게 수정
        elif isFiles ==0:
            sql = """ insert into file_table(filename,owner_id,filepath) values (%s,%s,%s)
                  """

            #rladnjsrb9999 대신 현재 유저
            cursor.execute(sql,(fileToUPLOAD.name,user_email,filepath))
            db.commit()
            cursor.close()

            return redirect('/files/'+pre_url)#그 직전 경로로 이동하게 수정

def new_folder(request):
    if request.method =='GET':
        return render(request, 'index.html')#그 직전 경로로 이동하게 수정
    if request.method =='POST':
        user_email = request.COOKIES.get('khustagram_login')
        new_folder_name = request.POST.get('new_folder_name')
        cur_url = request.POST.get('cur_url')
        print(cur_url)
        cururls = cur_url.split('/')
        print (cururls)
        #rladnjsrb9999에 현재 세션의 유저아이디 들어가야댐.
        parsed_url=''
        for index in range(0,len(cururls)):
            if index > 4:
                parsed_url+='/'+cururls[index]

        print(parsed_url)


        #folder path
        folder = str(new_folder_name)+"/"
        folder_name =user_email+parsed_url+folder
        #db에 있는 filepath
        filepath_in_db = user_email+parsed_url
        #이전 경로
        pre_url = filepath_in_db

        #S3에 추가
        session = boto3.session.Session(aws_access_key_id = AWS_ACCESS_KEY,
                                aws_secret_access_key = AWS_SECRET_KEY,
                                region_name = REGION_NAME)
        s3 = session.resource('s3')
        s3.Bucket(BUCKET_NAME).put_object(Key = folder_name, Body ="")

        #table에 추가
        db = pymysql.connect(host='localhost', user='root',passwd='hshadow189', db='khustagram', port=3306)
        cursor = db.cursor()

        #현재 파일 경로와 넣으려는 파일 이름을 넣기
        check_sql ="""select filename from file_table WHERE filepath=%s
        AND filename = %s
        """
        #있으면 1반환(row 개수)
        isFiles = cursor.execute(check_sql,(filepath_in_db,folder))
        print(isFiles)
        if isFiles == 1:
            sql = """ update file_table SET ts=%s WHERE filepath=%s AND filename=%s
                    """

            cursor.execute(sql,(datetime.now(),filepath_in_db,folder))
            db.commit()
            cursor.close()

            return redirect('/files/'+pre_url)#그 직전 경로로 이동하게 수정
        elif isFiles ==0:
            sql = """ insert into file_table(filename,owner_id,filepath) values (%s,%s,%s)
                          """

            #rladnjsrb9999 세션 유저 아이디로
            cursor.execute(sql,(folder,user_email,filepath_in_db))
            db.commit()
            cursor.close()

            return redirect('/files/'+pre_url)#그 직전 경로로 이동하게 수정

def files(request, filepath):

    #db로 쿼리문이용해 현재 경로에 맞게 보여주기
    print(filepath)
    para_path = filepath+"/"
    db = pymysql.connect(host='localhost', user='root',passwd='hshadow189', db='khustagram', port=3306)
    cursor = db.cursor()
    select_sql ="""
    select * from file_table WHERE filepath=%s
    """
    cursor.execute(select_sql,(para_path))
    rows = cursor.fetchall()
    context={
    'user_email' : request.COOKIES.get('khustagram_login'),
    'cur_items' : rows,
    'cur_place' : "/files/"+para_path
    }
    db.commit()
    cursor.close()
    return render(request, 'file_home.html', context)

def delete(request):

    cur_url = request.POST.get('cur_url')
    print(cur_url)
    urls=cur_url.split('/')

    file_url=''
    for i in range(0,len(urls)-1):
        if i>1:
            file_url+=urls[i]+"/"

    print(file_url)
    deleted_name = request.POST.get('deleted_name')
    print(deleted_name)

    key =file_url+deleted_name
    print(key)
    if(key[len(key)-1]=='/'):
        key=key[:-1]
    print(key)

    #S3에서 삭제
    s3 = boto3.client('s3',
    aws_access_key_id = AWS_ACCESS_KEY,
    aws_secret_access_key = AWS_SECRET_KEY,
    )
    s3.delete_object(Bucket=BUCKET_NAME , Key=key)

    #mysql에서 삭제
    db = pymysql.connect(host='localhost', user='root',passwd='hshadow189', db='khustagram', port=3306)
    cursor = db.cursor()
    delete_sql ="""
    delete from file_table WHERE filepath=%s AND filename=%s
    """
    cursor.execute(delete_sql,(file_url,deleted_name))
    db.commit()
    cursor.close()
    return redirect(cur_url)


#def viewing(request,viewing_path):


    #public and download and viewing

#    print(viewing_path)
#    places=viewing_path.split('/')
#    filename=places[len(places)-1]
#    s3 = boto3.client('s3',
#   aws_access_key_id = AWS_ACCESS_KEY,
#    aws_secret_access_key = AWS_SECRET_KEY,
#    )

#    s3.put_object_acl(ACL='public-read',Bucket=BUCKET_NAME ,Key = viewing_path)

#    s32 = boto3.resource('s3',
#    aws_access_key_id = AWS_ACCESS_KEY,
#    aws_secret_access_key = AWS_SECRET_KEY,
#    )

#    s32.Bucket(BUCKET_NAME).download_file(viewing_path, filename)

#    print(filename)
#    fpath =os.getcwd()+'/'+filename

#    print(fpath)
#    context = {
#    'filepath' :fpath,
#    }
#    webbrowser.open_new_tab(fpath)
#    return render(request, 'viewfile.html',context)

def viewing(request,viewing_path):


    #public and download and viewing

    places=viewing_path.split('/')
    filename=places[len(places)-1]
    s3 = boto3.client('s3',
    aws_access_key_id = AWS_ACCESS_KEY,
    aws_secret_access_key = AWS_SECRET_KEY,
    )

    s3.put_object_acl(ACL='public-read',Bucket=BUCKET_NAME ,Key = viewing_path)

    s32 = boto3.resource('s3',
    aws_access_key_id = AWS_ACCESS_KEY,
    aws_secret_access_key = AWS_SECRET_KEY,
    )

    s32.Bucket(BUCKET_NAME).download_file(viewing_path, filename)

    print(filename)
    fpath =os.getcwd()+'/'+filename

    print(fpath)
    context = {
    'filepath' :fpath,
    }
    
    filepath = os.path.join(mysite.settings.BASE_DIR, filename)
    filename = os.path.basename(filepath) # 파일명만 반환

    with open(filepath, 'rb') as f:
        response = HttpResponse(f)
        return response

def download(request):
    cur_url = request.POST.get('cur_url')
    print(cur_url)
    urls=cur_url.split('/')

    file_url=''
    for i in range(0,len(urls)-1):
        if i>1:
            file_url+=urls[i]+"/"

    print(file_url)
    #not public download
    download_name = request.POST.get('download_name')
    print(download_name)

    key =file_url+download_name
    print(key)
    # if(key[len(key)-1]=='/'):
    #     key=key[:-1]
    # print(key)

    s3 = boto3.resource('s3',
    aws_access_key_id = AWS_ACCESS_KEY,
    aws_secret_access_key = AWS_SECRET_KEY,
    )

    s3.Bucket(BUCKET_NAME).download_file(key, download_name)


    # 현재 프로젝트 최상위 (부모폴더) 밑에 있는 'scimagojr-3.xlsx' 파일
    filepath = os.path.join(mysite.settings.BASE_DIR, download_name)
    filename = os.path.basename(filepath) # 파일명만 반환

    with open(filepath, 'rb') as f:
        response = HttpResponse(f, content_type='application/force-download')
        # 필요한 응답헤더 세팅
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        return response
    return redirect(cur_url)
