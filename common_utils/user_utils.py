def is_user_superuser(request):
    if request.user.is_superuser or request.user.zr_admin_user.role.name == "ADMINSTAFF":
        return True
    else:
        return False

