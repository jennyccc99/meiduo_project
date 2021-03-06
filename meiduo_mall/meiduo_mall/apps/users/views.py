import re
from django import http
from django.contrib.auth import login, authenticate, logout
from django.db import DatabaseError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django_redis import get_redis_connection
from django.contrib.auth.mixins import LoginRequiredMixin

from users.models import User
from meiduo_mall.utils.response_code import RETCODE
from .utils import get_user_by_account


class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):
        # if request.user.is_authenticated:
        #     return render(request, "user_center_info.html")
        # else:
        #     return redirect(reverse("users:login"))
        return render(request, "user_center_info.html")



class LogoutView(View):

     def get(self, request):
         # 清理session
         logout(request)
         # 退出登录，重定向到登录页
         response = redirect(reverse('contents:index'))
         # 退出登录时清除cookie中的username
         response.delete_cookie('username')

         return response

class LoginView(View):

    def get(self, request):
        """提供用户登陆页面"""
        return render(request, "login.html")

    def post(self, request):
        """实现用户登陆逻辑"""
        # 接受参数
        username = request.POST.get("username")
        password = request.POST.get("password")
        remembered = request.POST.get("remembered")
        # 校验参数
        if not all([username, password]):
            return http.HttpResponseForbidden("缺少必传参数")

        # 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入正确的用户名或手机号')

        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')

        # 认证用户：先看用户是否存在，如果存在，再核对密码
        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, "login.html", {"account_errmsg": "账号或密码错误"})

        # 状态保持
        login(request, user)
        # remember状态保持周期
        if remembered != "on":
            request.session.set_expiry(0) # unit is second
        else:
            request.session.set_expiry(None) # 默认是两周

        # 响应结果，先取出next
        next = request.GET.get('next')
        if next:
            response = redirect(next)
        else:
            response = redirect(reverse('contents:index'))

        # 登录时用户名写入到cookie，有效期15天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        # 响应结果
        return response


class UsernameCountView(View):
    """判断用户名是否重复"""
    def get(self, request, username):
        """
        :param request: 请求对象
        :param username: 用户名
        :return: JSON
        """
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})

class MobileCountView(View):
    """判断手机号是否重复注册"""

    def get(self, request, mobile):
        """
        :param request: 请求对象
        :param mobile: 手机号
        :return: JSON
        """
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})

class RegisterView(View):
    """提供用户注册页面"""
    def get(self, request):
        return render(request, "register.html")

    def post(self, request):
        """实现用户注册业务逻辑"""
        # 接受参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client= request.POST.get("sms_code")
        allow = request.POST.get('allow')
        # 校验参数
        # 判断参数是否齐全
        if not all([username, password, password2, mobile, allow]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 判断两次密码是否一致
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
        # 判断短信验证码是否输入正确
        redis_conn = get_redis_connection("verify_code")
        sms_code_server = redis_conn.get("sms_%s" % mobile)
        if sms_code_server is None:
            return render(request, "register.html", {"sms_code_errmsg": "短信验证码已失效"})
        if sms_code_client != sms_code_server.decode():
            return render(request, "register.html", {"sms_code_errmsg": "输入短信验证码有误"})

        # 判断是否勾选用户协议
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # return render(request, "register.html", {'register_errmsg': '注册失败'})
        try:
            user = User.objects.create_user(username=username, password=password,mobile=mobile)
        except DatabaseError:
            return render(request, "register.html", {'register_errmsg': '注册失败'})

        # 实现状态保持
        login(request, user)

        response = redirect(reverse('contents:index'))
        # 注册时用户名写入到cookie，有效期15天
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)

        # 响应结果
        return response
        # return redirect(reverse("contents:index"))