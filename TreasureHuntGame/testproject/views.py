import json
from bson.objectid import ObjectId
from django.http.response import JsonResponse
from TreasureHuntGame.settings import db
from django.shortcuts import render

from .function import check_login, get_user, check_gold_backpack, check_wear, create_user, get_items, obj2str

# Create your views here.

@check_login
def test_getall_view(request):
    # 判断数据库是否连接
    if db is None:
        return JsonResponse({'error':'服务器有误，请重试'})
    
    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    # 从数据库中获取玩家的items
    wearitems = list(db.item.find({'buid':ObjectId(uid), 'state':'wear'}))
    backpackitems = list(db.item.find({'$or':[{'buid':ObjectId(uid),'state':'backpack'}, {'buid':ObjectId(uid),'state':'onsale'}]}))

    return JsonResponse({
        'user':obj2str(user),
        'wearitems':obj2str(wearitems),
        'backpackitems':obj2str(backpackitems),
    })

def test_user_view(request):
    # 判断数据库是否连接
    if db is None:
        return JsonResponse({'error':'服务器有误，请重试'})

    # 获取json文件内容
    try:
        f, username, password = request.GET['f'], request.GET['username'], request.GET['password']
    except Exception as e:
        print('请使用规定json格式')
        return JsonResponse({'error':'请使用规定json格式'})

    # 判断是注册操作
    if f == 'register':

        # 用户名是否可用
        user = db.user.find_one({'username':username})
        if user is not None:
            return JsonResponse({'error':'用户名重复，请重新输入'})

        # 编写文档，直接存入，密码未hash
        user = create_user(username, password)
        
        # 向数据库插入数据 要try 防止并发
        try:
            db.user.insert_one(user)

        except Exception as e:
            print('--- concurrent write error! ---')
            return JsonResponse({'error':'服务器有误，请重试'})
        
        return JsonResponse({'success':'注册成功，请登录'})

    # 判断是登录操作
    elif f == 'login':

        # 对比数据库用户和密码，然后进入个人界面
        user = db.user.find_one({'username':username})

        # 用户名不存在或密码错误
        if user is None or user['password'] != password:
            return JsonResponse({'error':'用户名或密码错误，请重试'})

        # 登录进入，且设置session
        else:
            request.session['username'] = user['username']
            request.session['uid'] = str(user['_id'])
            return JsonResponse({'success':'登录成功'})

    # 判断是退出登录操作
    elif f == 'logout':
         # 删除session值
        if 'username' in request.session and 'uid' in request.session:
            del request.session['username']
            del request.session['uid']
            
            return JsonResponse({'success':'退出登录成功'})
        else:
            return JsonResponse({'error':'您尚未登录，请登录'})
        
    else:
        print('请使用规定json格式')
        return JsonResponse({'error':'请使用规定json格式'})

@check_login
def test_work_view(request):
    
    # 判断数据库是否连接
    if db is None:
        return JsonResponse({'error':'服务器有误，请重试'})
    
    max_gold = 99999

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    try:
        work = request.GET['work']
    except Exception as e:
        print('请使用规定json格式')
        return JsonResponse({'error':'请使用规定json格式'})

    # 更改user数据
    user['gold_num'] += 10 * user['work_efficiency']

    # 金币数量能超过上限
    if user['gold_num'] > max_gold:
        user['gold_num'] = max_gold

    # 更新user数据库
    try:
        db.user.update({'_id':ObjectId(uid)}, user)
    except Exception as e:
        print('--- concurrent write error! ---')
        return JsonResponse({'error':'服务器有误，请重试'})

    return JsonResponse({'success':'成功工作，金币增加了'})

@check_login
def test_hunt_view(request):
    
    # 判断数据库是否连接
    if db is None:
        return JsonResponse({'error':'服务器有误，请重试'})

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    try:
        times = int(request.GET['times'])
        if times > 10:
            return JsonResponse({'error':'连抽次数过多！'})
    except Exception as e:
        print('请使用规定json格式')
        return JsonResponse({'error':'请使用规定json格式'})

    flag, warning = check_gold_backpack(user, 10*times, times)
    if flag is False:
        return JsonResponse({'error':warning})

    user['gold_num'] -= 10*times

    # 根据次数和幸运值获取宝物
    items = get_items(times, int(user['lucky_value']))

    # 向数据库插入新的item数据
    for item in items:
        item['buid'] = user['_id']  # 更改属于的用户id
        db.item.insert_one(item)
        item['iid'] = item['_id']   # 增加此字段仅方便前端访问(受django模板层限制变量不能以下划线开头)

        # 更改user的背包中宝物个数
        user['backpack'] += 1

    # 更新user数据库
    try:
        db.user.update({'_id':ObjectId(uid)}, user)
    except Exception as e:
        print('--- concurrent write error! ---')
        return JsonResponse({'error':'服务器有误，请重试'})

    return JsonResponse({
        'success':'成功获得宝物！以下是您获得的宝物：',
        'items':obj2str(items),
    })

@check_login
def test_operate_view(request):
    
    # 判断数据库是否连接
    if db is None:
        return JsonResponse({'error':'服务器有误，请重试'})

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    try:
        f, iid = request.GET['f'], request.GET['iid']
        # 获取iid所对应的item文档
        item = db.item.find_one({'_id':ObjectId(iid)})
    except Exception as e:
        print('请使用规定json格式')
        return JsonResponse({'error':'请使用规定json格式'})

    # 如果没有此宝物 或 判断是否为当前用户操作，防止恶意篡改
    if item is None or str(item['buid']) != str(uid):
        return JsonResponse({'error':'您没有此宝物！'})

    # 如果是佩戴请求
    if f == 'wear':

        # 判断是否还能佩戴
        flag, warning = check_wear(user, item)
        if flag == False:
            return JsonResponse({'error':warning})
        
        # 判断是否在背包里
        if item['state'] == 'wear':
            return JsonResponse({'error':'您已佩戴此宝物'})
        elif item['state'] == 'onsale':
            return JsonResponse({'error':'此宝物正在挂牌中，无法佩戴'})
        
        else:
            item['state'] = 'wear'
            user['work_efficiency'] += item['work_efficiency']
            user['lucky_value'] += item['lucky_value']
            user['wear'][(item['type']+'_num')] += 1

            # 更新数据库
            try:
                db.user.update({'_id':ObjectId(uid)}, user)
                db.item.update({'_id':ObjectId(iid)}, item)
            except Exception as e:
                print('--- concurrent write error! ---')
                return JsonResponse({'error':'服务器有误，请重试'})

        return JsonResponse({'success':'佩戴成功！'})
    
    # 如果是取下请求
    elif f == 'backpack':
        # 判断是否佩戴中
        if item['state'] == 'wear':
            item['state'] = 'backpack'
            user['work_efficiency'] -= item['work_efficiency']
            user['lucky_value'] -= item['lucky_value']
            user['wear'][(item['type']+'_num')] -= 1

            # 更新数据库
            try:
                db.user.update({'_id':ObjectId(uid)}, user)
                db.item.update({'_id':ObjectId(iid)}, item)
            except Exception as e:
                print('--- concurrent write error! ---')
                return JsonResponse({'error':'服务器有误，请重试'})
        else:
            return JsonResponse({'error':'此宝物并未佩戴！'})

        return JsonResponse({'success':'取下成功！'})

    # 如果是丢弃请求
    elif f == 'discard':

        # 判断是否在背包中
        if item['state'] == 'wear':
            return JsonResponse({'error':'您已佩戴此宝物，无法丢弃'})
        elif item['state'] == 'onsale':
            return JsonResponse({'error':'此宝物正在挂牌中，无法丢弃'})
        
        else:

            # 将背包信息更新
            user['backpack'] -= 1

            # 更新数据库
            try:
                db.user.update({'_id':ObjectId(uid)}, user)
                db.item.delete_one({'_id':ObjectId(iid)})
            except Exception as e:
                print('--- concurrent write error! ---')
                return JsonResponse({'error':'服务器有误，请重试'})

        return JsonResponse({'success':'丢弃成功！'})

    else:
        return JsonResponse({'error':'请使用规定json格式'})

@check_login
def test_market_view(request):
    
    # 判断数据库是否连接
    if db is None:
        return JsonResponse({'error':'服务器有误，请重试'})

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    try:
        f = request.GET['f']
        if f == 'view':
            items = list(db.item.find({'buid':{'$ne':ObjectId(uid)}, 'state':'onsale'}))
            return JsonResponse({
                'success':'以下为商城中正在出售的宝物：',
                'items':obj2str(items)
            })

        iid = request.GET['iid']
        # 获取iid所对应的item文档
        item = db.item.find_one({'_id':ObjectId(iid)})
    except Exception as e:
        print('请使用规定json格式')
        return JsonResponse({'error':'请使用规定json格式'})

    # 如果没有此宝物
    if item is None:
        return JsonResponse({'error':'此宝物不存在！'})
    
    # 购买请求
    if f == 'buy':
        # # 判断是否为当前用户操作，防止自己购买自己的宝物
        # if str(item['buid']) == str(uid):
        #     return JsonResponse({'error':'这是您自己的宝物！'})

        # 判断是否onsale
        if item['state'] == 'onsale':

            # 判断是否能购买
            flag, warning = check_gold_backpack(user, item['price'], 1)
            if flag is False:
                return JsonResponse({'error':warning})

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
                print('--- concurrent write error! ---')
                return JsonResponse({'error':'服务器有误，请重试'})

            return JsonResponse({'success':'成功购买宝物！快去佩戴吧！'})

        # 若不是onsale
        else:
            return JsonResponse({'error':'此宝物并没有挂牌出售！'})

    # 出售请求
    elif f == 'sell':
        # 判断是否为当前用户操作，防止恶意篡改
        if str(item['buid']) != str(uid):
            return JsonResponse({'error':'您没有此宝物！'})

        # 获取挂牌价格
        try:
            price = int(request.GET['price'])
        except Exception as e:
            print('--- 价格输入有误 ---')
            return JsonResponse({'error':'输入价格有误！'})

        # 判断是否在背包中(或者正在售卖，此时为更新价格)
        if item['state'] == 'backpack' or item['state'] == 'onsale':
            
            item['state'] = 'onsale'
            item['price'] = price

            # 更新数据库
            try:
                db.item.update({'_id':ObjectId(iid)}, item)
            except Exception as e:
                print('--- concurrent write error! ---')
                return JsonResponse({'error':'服务器有误，请重试'})

            return JsonResponse({'success':'成功挂牌宝物！等待有缘人购买吧！'})

        # 如果宝物状态是佩戴中则无法挂牌出售
        else:
            return JsonResponse({'error':'您正在佩戴此宝物！无法挂牌出售！'})

    # 回收请求
    elif f == 'retrieve':
        # 判断是否为本人操作，防止恶意篡改
        if str(item['buid']) != str(uid):
            return JsonResponse({'error':'您没有此宝物！'})

        # 判断是否在onsale中
        if item['state'] == 'onsale':

            item['state'] = 'backpack'
            item['price'] = 0

            # 更新数据库
            try:
                db.item.update({'_id':ObjectId(iid)}, item)
            except Exception as e:
                print('--- concurrent write error! ---')
                return JsonResponse({'error':'服务器有误，请重试'})

            return JsonResponse({'success':'成功回收挂牌宝物！'})
        
        # 如果宝物状态不是onsale
        else:
            return JsonResponse({'error':'此宝物并未挂牌出售！'})

    else:
        print('请使用规定json格式')
        return JsonResponse({'error':'请使用规定json格式'})