import uuid


def is_user_superuser(request):
    if request.user.is_authenticated():
        if request.user.is_superuser or request.user.zr_admin_user.role.name == "ADMINSTAFF":
            return True
    return False


def get_unique_id():
    return uuid.uuid4()


def file_save_s3(file_obj, directory="default", user_id=""):
    import boto3

    # Let's use Amazon S3
    s3 = boto3.client('s3', region_name='ap-south-1', api_version=None,
                      use_ssl=True, verify=None, endpoint_url='https://s3.ap-south-1.amazonaws.com',
                      aws_access_key_id='AKIAI4Y5NO3K36LXYYVQ',
                      aws_secret_access_key='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',
                      aws_session_token=None, config=None)
    # Create unique file name
    file_name = str(get_unique_id()) + '.' + (file_obj._get_name().split('.')[-1].lower())
    s3.upload_fileobj(file_obj, "zrupee-credit-request-documents", file_name, ExtraArgs={'ACL': 'public-read'})
    s3_url = "{}/{}/{}".format('https://s3.ap-south-1.amazonaws.com', "zrupee-credit-request-documents", file_name)
    return s3_url
