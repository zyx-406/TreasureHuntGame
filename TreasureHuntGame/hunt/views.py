from bson.objectid import ObjectId
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from user.views import get_user, check_login, check_gold_backpack, server_error

from TreasureHuntGame.settings import db

# Create your views here.

def create_item(item_type):
    return {
        'buid':'',
        'name':item_type['name'],
        'grade':item_type['grade'],
        'info':item_type['info'],
        'type':item_type['type'],
        'work_efficiency':item_type['work_efficiency'],
        'lucky_value':item_type['lucky_value'],
        'state':'backpack',
        'price':0,
    }

def get_items(times, lucky_value):
    import numpy as np
    import random

    # 构建item资源池
    items_all_num = 100000
    items_poor = []
    item_list = db.item_type.find()
    for item_type in item_list:
        if item_type['myid'] != 0:
            prob = float(item_type['prob'])
            num = int(prob * (1+lucky_value*0.02) * items_all_num) # 可能性算法
            items_poor.extend(list(np.full(num, item_type['myid'])))
    
    # 用0补充
    if (items_all_num-len(items_poor)) > 0:
        items_poor.extend(list(np.zeros(items_all_num-len(items_poor))))

    # 从item资源池中获取一个item，并封装成item文档
    items = []
    for i in range(times):
        items.append(create_item(db.item_type.find_one({'myid':int(random.choice(items_poor))})))
    return items

@check_login
def hunt_view(request):

    # 判断数据库是否连接
    if db is None:
        return server_error(request, '数据库连接错误')

    # 获取username, uid, 和user文档
    username, uid, user = get_user(request)

    if request.method == 'GET':

        # 如果请求中包含times
        if 'times' in request.GET:
            times = request.GET['times']

            # 获取times并判断能否购买
            if times == '1':

                # 判断是否能购买
                flag, warning = check_gold_backpack(user, 10, 1)
                if flag is False:
                    return render(request, 'home/home.html', dict({'warning':warning}, **user))

                times = 1
                user['gold_num'] -= 10
            else:
                ####### 此处可加入十连抽等 #######
                return HttpResponseRedirect('操作错误')

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
                server_error(request)

            return render(request, 'home/item.html', {'item':items[0], 'again':True})

        else:
            ####### 如果hunt使用单独页面可以在此修改 ########
            return HttpResponseRedirect('/home')
        

    elif request.method == 'POST':
        return HttpResponseRedirect('/home')