from bson.objectid import ObjectId
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from user.views import check_login, server_error, get_user

from TreasureHuntGame.settings import db

# Create your views here.

max_gold = 99999

@check_login
def work_view(request):
    
    # 判断数据库是否连接
    if db is None:
        return server_error(request, '数据库连接错误')

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    if request.method == 'GET':

        # 如果请求中包含work
        if 'work' in request.GET:

            # 更改user数据
            user['gold_num'] += 10*user['work_efficiency']
            if user['gold_num'] > max_gold:
                user['gold_num'] = max_gold

            # 更新user数据库
            try:
                db.user.update({'_id':ObjectId(uid)}, user)
            except Exception as e:
                server_error(request)

            return HttpResponseRedirect('/home')

        else:
            ####### 如果work使用单独页面可以在此修改 ########
            return HttpResponseRedirect('/home')

    else:

        return HttpResponseRedirect('/home')