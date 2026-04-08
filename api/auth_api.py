"""
用户认证API模块
提供用户注册、登录等认证相关接口
"""

from flask import Blueprint, request
from core.auth.user_auth import UserAuth
from .utils import APIResponse, handle_api_error
from .auth_middleware import generate_token, require_auth, get_current_user

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 初始化认证管理器
user_auth = UserAuth()

@auth_bp.route('/register', methods=['POST'])
@handle_api_error
def register():
    """用户注册"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password:
        return APIResponse.error('用户名和密码不能为空', 400)

    result = user_auth.register(username, password, email)
    if result['success']:
        # 注册成功后自动生成 token
        token = generate_token(result.get('user_id'), username)
        return APIResponse.success({
            'user_id': result.get('user_id'),
            'username': username,
            'token': token
        }, result['message'])
    else:
        return APIResponse.error(result['message'], 400)

@auth_bp.route('/login', methods=['POST'])
@handle_api_error
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return APIResponse.error('用户名和密码不能为空', 400)

    result = user_auth.login(username, password)
    if result['success']:
        # 生成 JWT token
        token = generate_token(result.get('user_id'), username)
        return APIResponse.success({
            'user_id': result.get('user_id'),
            'username': username,
            'token': token
        }, result['message'])
    else:
        return APIResponse.error(result['message'], 401)


@auth_bp.route('/verify', methods=['GET'])
@handle_api_error
@require_auth
def verify_token():
    """验证 Token 是否有效"""
    user = get_current_user()
    return APIResponse.success({
        'user_id': user['user_id'],
        'username': user['username']
    }, "Token 有效")


@auth_bp.route('/profile', methods=['GET'])
@handle_api_error
@require_auth
def get_current_profile():
    """获取当前登录用户信息（从 JWT token 解析，无需传 user_id）"""
    user = get_current_user()
    info = user_auth.get_user_info(user['user_id'])
    if not info:
        return APIResponse.error('用户不存在', 404)
    for k in ['password_hash', 'model_filename']:
        info.pop(k, None)
    return APIResponse.success(info, "获取个人信息成功")


@auth_bp.route('/profile/<int:user_id>', methods=['GET'])
@handle_api_error
@require_auth
def get_profile(user_id):
    """查询个人信息"""
    # 验证当前用户只能查看自己的信息
    current_user = get_current_user()
    if current_user['user_id'] != user_id:
        return APIResponse.error('无权访问', 403)

    info = user_auth.get_user_info(user_id)
    if not info:
        return APIResponse.error('用户不存在', 404)
    for k in ['password_hash', 'model_filename']:
        info.pop(k, None)
    return APIResponse.success(info, "获取个人信息成功")


@auth_bp.route('/profile/<int:user_id>', methods=['PUT'])
@handle_api_error
@require_auth
def update_profile(user_id):
    """更新个人信息"""
    # 验证当前用户只能修改自己的信息
    current_user = get_current_user()
    if current_user['user_id'] != user_id:
        return APIResponse.error('无权修改', 403)

    from tools.users_crud import UsersCRUD
    data = request.get_json()
    crud = UsersCRUD()
    user = crud.read(user_id)
    if not user:
        return APIResponse.error('用户不存在', 404)
    fields = {}
    for k in ['student_no', 'real_name', 'email']:
        if k in data:
            fields[k] = data[k]
    if fields:
        crud.update(user_id, **fields)
    updated = crud.read(user_id)
    for k in ['password_hash', 'model_filename']:
        updated.pop(k, None)
    return APIResponse.success(updated, "更新成功")


@auth_bp.route('/password/<int:user_id>', methods=['PUT'])
@handle_api_error
@require_auth
def change_password(user_id):
    """修改密码"""
    # 验证当前用户只能修改自己的密码
    current_user = get_current_user()
    if current_user['user_id'] != user_id:
        return APIResponse.error('无权修改', 403)

    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return APIResponse.error('旧密码和新密码不能为空', 400)

    if len(new_password) < 6:
        return APIResponse.error('新密码至少需要6个字符', 400)

    # 验证旧密码
    result = user_auth.login(current_user['username'], old_password)
    if not result['success']:
        return APIResponse.error('旧密码错误', 400)

    # 更新密码
    from tools.users_crud import UsersCRUD
    crud = UsersCRUD()

    # 生成新密码哈希
    import bcrypt
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    crud.update(user_id, password_hash=password_hash)

    return APIResponse.success({}, "密码修改成功")
