from bson.objectid import ObjectId
from django.shortcuts import render
from django.http import HttpResponseRedirect

from TreasureHuntGame.settings import db

# Create your views here.

# user文档
def create_user(username, password):
    return {
        'username':username,
        'password':password,
        'gold_num':100,
        'work_efficiency':1,
        'lucky_value':1,
        'wear':{
            'tool_num':0,
            'ornament_num':0,
            'totipotent_num':0,
        },
        'backpack':0,
        'auto_clean':0,
    }

max_num = 60
# 检查用户金币是否不足或背包是否有空
def check_gold_backpack(user, gold, num):

    if user['gold_num'] < gold:
        return False, '金币不足'
    if (user['backpack'] + num) > max_num:
        return False, '背包空间不足'

    return True, ''

max_tool, max_ornament, max_totipotent = 2, 2, 1
# 检查用户是否能佩戴宝物
def check_wear(user, item):

    if item['type'] == 'totipotent':
        if user['wear']['tool_num'] > 0 or user['wear']['ornament_num'] > 0:
            return False, '有且只能佩戴一个全能宝物，此时将无法佩戴其他宝物！'
    elif item['type'] == 'tool':
        if user['wear']['tool_num'] >= max_tool:
            return False, '佩戴工具已达上限！'
        elif user['wear']['totipotent_num'] >= max_totipotent:
            return False, '有且只能佩戴一个全能宝物，此时将无法佩戴其他宝物！'
    elif item['type'] == 'ornament':
        if user['wear']['ornament_num'] >= max_tool or user['wear']['totipotent_num'] > max_totipotent:
            return False, '佩戴饰品已达上限！'
        elif user['wear']['totipotent_num'] >= max_totipotent:
            return False, '有且只能佩戴一个全能宝物，此时将无法佩戴其他宝物！'
    else:
        return False, '无效宝物无法佩戴！'

    return True, ''

# 服务器有误的报错以及界面
def server_error(request, warning='服务器有误，请重试'):
    print('--- Server Error!(maybe concurrent or database disconnect) ---')
    return render(request, 'server_error.html', warning)

# 返回username, uid, 和user文档
def get_user(request):

    # 获取session中的username，uid
    username = request.session['username']
    uid = request.session['uid']
    
    # 从数据库中获取玩家文档
    user = db.user.find_one({'_id':ObjectId(uid)})

    return username, uid, user

# 检查用户是否已登录的装饰器
def check_login(fn):
    def wrap(request, *args, **kwargs):
        if 'username' not in request.session or 'uid' not in request.session:
            warning_dic = {'warning':'用户登录已过期，请重新登录'}
            return render(request, 'user/login.html', warning_dic)
        return fn(request, *args, **kwargs)
    return wrap

def login_view(request):
    if request.method == 'GET':
        # 如果有session
        if 'username' in request.session and 'uid' in request.session:
            from home.views import home_view
            return home_view(request)

        # 如果没有session
        return render(request, 'user/login.html')

    elif request.method == 'POST':
        # 判断数据库是否连接
        if db is None:
            warning_dic = {'warning':'服务器有误，请重试'}
            return render(request, 'user/login.html', warning_dic)

        # 获取请求中的username和password
        username = request.POST['username']
        password = request.POST['password']

        # 对比数据库用户和密码，然后进入个人界面
        user = db.user.find_one({'username':username})

        # 用户名不存在或密码错误
        if user is None or user['password'] != password:
            warning_dic = {'warning':'用户名或密码错误，请重试'}
            return render(request, 'user/login.html', warning_dic)

        # 登录进入，且设置session
        else:
            request.session['username'] = user['username']
            request.session['uid'] = str(user['_id'])
            return HttpResponseRedirect('/home/')

    else:
        return render(request, 'user/login.html')

def register_view(request):
    if request.method == 'GET':
        return render(request, 'user/register.html')

    elif request.method == 'POST':
        # 获取请求中的username和password
        username = request.POST['username']
        password = request.POST['password']

        # 密码一致性检查，这里忽略
        pass

        # 判断数据库是否连接
        if db is None:
            warning_dic = {'warning':'服务器有误，请重试'}
            return render(request, 'user/register.html', warning_dic)

        # 用户名是否可用
        user = db.user.find_one({'username':username})
        if user is not None:
            warning_dic = {'warning':'用户名重复，请修改用户名'}
            return render(request, 'user/register.html', warning_dic)

        # 编写文档，直接存入，密码未hash
        user = create_user(username, password)
        
        # 向数据库插入数据 要try 防止并发
        try:
            db.user.insert_one(user)

        except Exception as e:
            print('--- concurrent write error! ---')
            warning_dic = {'warning':'服务器有误，请重试'}
            return render(request, 'user/register.html', warning_dic)
        
        # 返回时需要退出现登录账号，并跳转到登录界面
        return logout_view(request)

    else:
        return render(request, 'user/register.html')

def logout_view(request):
    # 删除session值
    if 'usrname' in request.session:
        del request.session['username']
    if 'uid' in request.session:
        del request.session['uid']

    return HttpResponseRedirect('/user/')