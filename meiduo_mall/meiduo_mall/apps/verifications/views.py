from django import http
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
import random, logging

from . import constants
from verifications.lib.captcha.captcha import captcha
from meiduo_mall.utils.response_code import RETCODE
from verifications.lib.yuntongxun.ccp_sms import CCP
from celery_tasks.sms.tasks import send_sms_code


# 创建日志输出器
logger = logging.getLogger("django")


class SMSCodeView(View):
    def get(self, request, mobile):
        """
        :param reqeust: 请求对象
        :param mobile: 手机号
        :return: JSON
        """
        # 接受参数
        image_code_client = request.GET.get("image_code")
        uuid = request.GET.get("uuid")

        # 校验参数
        if not all([image_code_client, uuid]):
            return http.HttpResponseForbidden("缺参数")

        redis_conn = get_redis_connection('verify_code')
        # 判断是否频繁发送验证码
        send_flag=redis_conn.get("send_flag_%s" % mobile)
        if send_flag:
            return http.JsonResponse({"code": RETCODE.THROTTLINGERR, "errmsg": "发送短信过于频繁"})
        #提取图形验证码
        image_code_server = redis_conn.get("img_%s' % uuid")
        if image_code_server is None:
            return http.JsonResponse({"code": RETCODE.IMAGECODEERR, "errmsg": "图形验证码已失效"})
        # 删除图形验证码
        redis_conn.delete("img_%s' % uuid")
        # 对比图形验证码
        image_code_server = image_code_server.decode()#转换bytes to strings for comparison
        if image_code_client.lower() != image_code_server.lower():#转小写字母来比较
            return http.JsonResponse({"code": RETCODE.IMAGECODEERR, "errmsg": "图形验证码有误"})
        # 生产短信验证码:随机6位数
        sms_code = '%06d' % random.randint(0, 999999)
        logger.info(sms_code) # 手动的输出日志，记录验证码

        # 创建Redis管道
        pl = redis_conn.pipeline()
        # 保存短信验证码
        pl.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # 保存发送验证码标记
        pl.setex("send_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        # 执行请求
        pl.execute()

        # 发送短信验证码
        # CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES//60], constants.SEND_SMS_TEMPLATE_ID)
        # 使用celery发送短信验证码
        send_sms_code.delay(mobile, sms_code)
        # 响应结果
        return http.JsonResponse({"code": RETCODE.OK, "errmsg": "发送短信成功"})


class ImageCodeView(View):
    def get(self, request, uuid):
        """
        :param request: 请求对象
        :param uuid: 唯一标识图形验证码所属于的用户
        :return: image/jpg
        """
        text, image = captcha.generate_captcha()
        redis_conn = get_redis_connection('verify_code')
        redis_conn.setex('img_%s' % uuid, constants.IMAGE_CODE_REDIS_EXPIRES, text)

        return http.HttpResponse(image, content_type="image/jpg")