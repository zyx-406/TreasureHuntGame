from bson.objectid import ObjectId
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from user.views import check_login, server_error, check_gold_backpack, get_user

from TreasureHuntGame.settings import db

# Create your views here.

def items_counting(items):
    total, tool, ornament, totipotent = 0,0,0,0
    for item in items:
        total += 1
        if item['type'] == 'totipotent':
            totipotent += 1
        if item['type'] == 'tool':
            tool += 1
        if item['type'] == 'ornament':
            ornament += 1

    return total, tool, ornament, totipotent

@check_login
def market_view(request):

    # 判断数据库是否连接
    if db is None:
        return server_error(request, '数据库连接错误')

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    if request.method == 'GET':
        
        # 判断有没有?f=xxx请求，此时跳转到f对应的界面
        if 'f' in request.GET:
            # 如果f是sell请求
            if request.GET['f'] == 'sell':
                # 从数据库中获取items数据(所有属于此用户的在背包中的宝物，不包含佩戴中)
                items = list(db.item.find({'$or':[{'buid':ObjectId(uid),'state':'backpack'}, {'buid':ObjectId(uid),'state':'onsale'}]}))

                total, tool, ornament, grade3 = items_counting(items)

                for item in items:
                    item['iid'] = item['_id']   # 增加此字段仅方便前端访问(受django模板层限制变量不能以下划线开头)

                dic = {'f':'出售',  'total':total, 'tool':tool, 'ornament':ornament, 'grade3':grade3, 'items':items}
                return render(request, 'market/market.html', dict(dic, **user))

        # 没有f默认返回购买页面
        else:
            # 从数据库中获取items数据(所有不等于此前uid的onsale宝物)
            items = list(db.item.find({'buid':{'$ne':ObjectId(uid)}, 'state':'onsale'}))

            total, tool, ornament, totipotent = items_counting(items)
                
            for item in items:
                    item['iid'] = item['_id']   # 增加此字段仅方便前端访问(受django模板层限制变量不能以下划线开头)

            dic = {'f':'购买', 'total':total, 'tool':tool, 'ornament':ornament, 'totipotent':totipotent, 'items':items}
            return render(request, 'market/market.html', dict(dic, **user))

    elif request.method == 'POST':

        dic = {}
        return render(request, 'market/market.html', dic)

@check_login
def item_view(request):

    # 判断数据库是否连接
    if db is None:
        return server_error(request, '数据库连接错误')

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)
    
    if request.method == 'GET':

        # 从数据库中获取item文档
        iid = request.GET['item'].replace('/', '')
        item = db.item.find_one({'_id':ObjectId(iid)})

        # 如果没有此宝物
        if item is None:
            return HttpResponse('操作错误')

        if 'f' in request.GET:
            f = request.GET['f']

            # 如果是购买请求
            if f == 'buy':
                # 判断是否onsale且是否不属于此用户
                if (item['state'] == 'onsale') and (str(item['buid']) != str(uid)):

                    # 判断是否能购买
                    flag, warning = check_gold_backpack(user, item['price'], 1)
                    if flag is False:
                        user['uid'] = user['_id']   # 增加此字段仅方便前端访问(受django模板层限制变量不能以下划线开头)
                        item['iid'] = item['_id']   # 增加此字段仅方便前端访问(受django模板层限制变量不能以下划线开头)
                        return render(request, 'market/market_item.html', {'item':item, 'user':user, 'warning':warning})

                    # 更新user信息
                    # 更新卖家
                    seller = db.user.find_one({'_id':ObjectId(item['buid'])})
                    seller['gold_num'] += item['price']
                    seller['backpack'] -= 1

                    # 更新买家
                    user['gold_num'] -= item['price']
                    user['backpack'] += 1

                    # 更新item信息
                    item['state'] = 'backpack'
                    item['buid'] = ObjectId(uid)
                    item['price'] = 0

                    # 更新数据库
                    try:
                        db.user.update({'_id':ObjectId(seller['_id'])}, seller)
                        db.user.update({'_id':ObjectId(uid)}, user)
                        db.item.update({'_id':ObjectId(iid)}, item)
                    except Exception as e:
                        server_error(request)

                    return HttpResponseRedirect('/market/')

                # 操作出错
                else:
                    return HttpResponse('操作出错')

            # 如果是回收请求retrieve
            else:
                # 判断是否在onsale中
                if (item['state'] == 'onsale') and (str(item['buid']) == str(uid)):

                    item['state'] = 'backpack'
                    item['price'] = 0

                    # 更新数据库
                    try:
                        db.item.update({'_id':ObjectId(iid)}, item)
                    except Exception as e:
                        server_error(request)

                    return HttpResponseRedirect('/market/?f=sell')

                # 操作出错
                else:
                    return HttpResponse('操作出错')
        
        else:
            user['uid'] = user['_id']   # 增加此字段仅方便前端访问(受django模板层限制变量不能以下划线开头)
            item['iid'] = item['_id']   # 增加此字段仅方便前端访问(受django模板层限制变量不能以下划线开头)
            return render(request, 'market/market_item.html', {'item':item, 'user':user})
    
    # 这里只有出售是POST请求故不区分operation
    elif request.method == 'POST':

        # 从数据库中获取item文档
        iid = request.POST['item'].replace('/', '')
        item = db.item.find_one({'_id':ObjectId(iid)})

        # 如果没有此宝物
        if item is None:
            return HttpResponse('操作失误')

        # 判断是否为当前用户操作，防止恶意篡改
        if str(item['buid']) != str(uid):
            return HttpResponse('操作错误')

        # 获取挂牌价格
        try:
            price = int(request.POST['price'])
        except Exception as e:
            print('--- 价格输入有误 ---')
            return HttpResponse('操作出错')

        # 判断是否在背包中(或者正在售卖，此时为更新价格)，且此物品属于session用户
        if (item['state'] == 'backpack' or item['state'] == 'onsale') and (str(item['buid']) == str(uid)):
            
            item['state'] = 'onsale'
            item['price'] = price

            # 更新数据库
            try:
                db.item.update({'_id':ObjectId(iid)}, item)
            except Exception as e:
                server_error(request)

            return HttpResponse('success')

        # 操作出错
        else:
            return HttpResponse('操作出错')
