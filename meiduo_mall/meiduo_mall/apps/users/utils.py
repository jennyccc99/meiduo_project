# self-define backend for user auth: both username and cellphone login
from django.contrib.auth.backends import ModelBackend
import re
from users.models import User


def get_user_by_account(account):
    """
    通过账号（用户名/手机）获取用户信息
    :param account: 用户名或者手机号
    :return: user
    """
    try:
        if re.match(r'^1[3-9]\d{9}$', account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class UsernameMobileBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
               重写认证方法，实现多账号登录
               :param request: 请求对象
               :param username: 用户名 or mobile #
               :param password: 密码
               :param kwargs: 其他参数
               :return: user
               """
        # search for user
        user = get_user_by_account(username)

        # verify if user exist and password matches
        if user and user.check_password(password):
            return user
        else:
            return None




