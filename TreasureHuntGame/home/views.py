from django.http.response import HttpResponse, HttpResponseRedirect, HttpResponseRedirectBase
from django.core.paginator import Paginator
from django.shortcuts import render
from bson.objectid import ObjectId
from user.views import check_login, server_error, check_wear, get_user

from TreasureHuntGame.settings import db

# Create your views here.

@check_login
def home_view(request):

    # 判断数据库是否连接
    if db is None:
        return server_error(request, '数据库连接错误')

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    return render(request, 'home/home.html', user)

@check_login
def my_view(request):

    # 判断数据库是否连接
    if db is None:
        return server_error(request, '数据库连接错误')

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    page_num = request.GET.get('page', 1)

    # 从数据库中获取玩家的items
    wearitems = list(db.item.find({'buid':ObjectId(uid), 'state':'wear'}))
    for item in wearitems:
        item['iid'] = item['_id']

    backpackitems = list(db.item.find({'$or':[{'buid':ObjectId(uid),'state':'backpack'}, {'buid':ObjectId(uid),'state':'onsale'}]}))
    for item in backpackitems:
        item['iid'] = item['_id']

    paginator = Paginator(backpackitems, 8)

    backpackitems_page = paginator.page(page_num)

    return render(request, 'home/my.html', dict({'wearitems':wearitems, 'backpackitems':backpackitems_page, 'page_range':paginator.page_range, 'page_num':page_num}, **user))

@check_login
def item_view(request):

    # 判断数据库是否连接
    if db is None:
        return server_error(request, '数据库连接错误')

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    # 从数据库中获取item文档
    iid = request.GET['item'].replace('/', '')
    item = db.item.find_one({'_id':ObjectId(iid)})

    # 如果没有此宝物
    if item is None:
        return HttpResponse('操作失误')

    # 判断是否为当前用户操作，防止恶意篡改
    if str(item['buid']) != str(uid):
        return HttpResponse('操作错误')
    
    if request.method == 'GET':

        if 'f' in request.GET:
            f = request.GET['f']

            # 如果是佩戴请求
            if f == 'wear':

                # 判断是否还能佩戴
                flag, warning = check_wear(user, item)
                if flag == False:
                    item['iid'] = item['_id']   # 增加此字段仅方便前端访问(受django模板层限制变量不能以下划线开头)
                    return render(request, 'home/item.html', {'item':item, 'warning':warning})

                # 判断是否在背包里
                if item['state'] == 'backpack':
                    item['state'] = 'wear'
                    user['work_efficiency'] += item['work_efficiency']
                    user['lucky_value'] += item['lucky_value']
                    if item['type'] == 'totipotent':
                        user['wear']['totipotent_num'] += 1
                    elif item['type'] == 'tool':
                        user['wear']['tool_num'] += 1
                    elif item['type'] == 'ornament':
                        user['wear']['ornament_num'] += 1
                    else:
                        pass

                    # 更新数据库
                    try:
                        db.user.update({'_id':ObjectId(uid)}, user)
                        db.item.update({'_id':ObjectId(iid)}, item)
                    except Exception as e:
                        server_error(request)

                return HttpResponseRedirect('/home/my/')

            # 如果是取下请求
            elif f == 'backpack':
                # 判断是否佩戴中
                if item['state'] == 'wear':
                    item['state'] = 'backpack'
                    user['work_efficiency'] -= item['work_efficiency']
                    user['lucky_value'] -= item['lucky_value']
                    if item['type'] == 'totipotent':
                        user['wear']['totipotent_num'] -= 1
                    elif item['type'] == 'tool':
                        user['wear']['tool_num'] -= 1
                    elif item['type'] == 'ornament':
                        user['wear']['ornament_num'] -= 1
                    else:
                        pass

                    # 更新数据库
                    try:
                        db.user.update({'_id':ObjectId(uid)}, user)
                        db.item.update({'_id':ObjectId(iid)}, item)
                    except Exception as e:
                        server_error(request)

                return HttpResponseRedirect('/home/my/')

            # 如果是丢弃请求
            else:
                # 判断是否在背包中
                if item['state'] == 'backpack':

                    # 将背包信息更新
                    user['backpack'] -= 1

                    # 更新数据库
                    try:
                        db.user.update({'_id':ObjectId(uid)}, user)
                        db.item.delete_one({'_id':ObjectId(iid)})
                    except Exception as e:
                        server_error(request)
                
                if f == 'dropandhunt':
                    return HttpResponseRedirect('/hunt/?times=1')

                return HttpResponseRedirect('/home/my/')
        
        else:
            item['iid'] = item['_id']   # 增加此字段仅方便前端访问(受django模板层限制变量不能以下划线开头)
            return render(request, 'home/item.html', {'item':item})
    
    else:
        return HttpResponse('/home')