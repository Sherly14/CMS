# Let's use Amazon S3
import os
import sys
import uuid

import boto3
from django.conf import settings

s3 = boto3.client('s3', region_name='ap-south-1', api_version=None,
                  use_ssl=True, verify=None, endpoint_url='https://s3.ap-south-1.amazonaws.com',
                  aws_access_key_id='AKIAI4Y5NO3K36LXYYVQ',
                  aws_secret_access_key='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',
                  aws_session_token=None, config=None)


def is_user_superuser(request):
    if request.user.is_authenticated():
        if request.user.is_superuser or request.user.zr_admin_user.role.name == "ADMINSTAFF":
            return True
    return False


def get_unique_id():
    return uuid.uuid4()


def file_save_s3(file_obj, directory="default", user_id=""):
    # Create unique file name
    file_name = str(get_unique_id()) + '.' + (file_obj._get_name().split('.')[-1].lower())
    # file_name = str(get_unique_id()) + '.' + (file_obj._get_name().split('.')[-1].lower())
    s3.upload_fileobj(file_obj, "zrupee-credit-request-documents", file_name, ExtraArgs={'ACL': 'public-read'})
    s3_url = "{}/{}/{}".format('https://s3.ap-south-1.amazonaws.com', "zrupee-credit-request-documents", file_name)
    return s3_url


def push_file_to_s3(file_path, file_name, bucket_name, timeout=600):
    with open(file_path, 'rb') as data:
        s3.upload_fileobj(data, bucket_name, file_name, ExtraArgs={'ACL': 'public-read'})
    # s3_url = "{}/{}/{}".format('https://s3.ap-south-1.amazonaws.com', bucket_name, file_name)
    s3_url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': bucket_name,
            'Key': file_name, },
        ExpiresIn=timeout, )
    os.remove(file_path)
    return s3_url
