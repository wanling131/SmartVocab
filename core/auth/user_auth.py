"""
用户认证模块
"""

from tools.users_crud import UsersCRUD
import bcrypt

class UserAuth:
    """用户认证类"""
    
    def __init__(self):
        self.users_crud = UsersCRUD()
    
    def register(self, username, password, email=None):
        """
        用户注册
        
        Args:
            username (str): 用户名
            password (str): 密码
            email (str): 邮箱（可选）
            
        Returns:
            dict: 注册结果
        """
        print(f"DEBUG UserAuth.register: username={username}, email={email}")
        
        # 检查用户名是否合法
        if not self._is_valid_username(username):
            print(f"DEBUG UserAuth.register: 用户名不合法 - {username}")
            return {"success": False, "message": "用户名不合法"}
        
        # 检查密码是否合法
        if not self._is_valid_password(password):
            print(f"DEBUG UserAuth.register: 密码不合法")
            return {"success": False, "message": "密码不合法"}
        
        # 检查用户名是否已存在
        if self._check_user_exists(username):
            print(f"DEBUG UserAuth.register: 用户名已存在 - {username}")
            return {"success": False, "message": "用户名已存在"}
        
        # 密码加密并创建用户
        password_hash = self._hash_password(password)
        # 处理空邮箱：将空字符串转换为None，避免唯一约束冲突
        email_to_save = email if email and email.strip() else None
        user_id = self.users_crud.create(username, password_hash, email_to_save)
        
        if user_id:
            print(f"DEBUG UserAuth.register: 注册成功，用户ID={user_id}")
            return {"success": True, "message": "注册成功", "user_id": user_id}
        else:
            print(f"DEBUG UserAuth.register: 创建用户失败")
            return {"success": False, "message": "注册失败"}
    
    def login(self, username, password):
        """
        用户登录
        
        Args:
            username (str): 用户名
            password (str): 密码
            
        Returns:
            dict: 登录结果
        """
        print(f"DEBUG UserAuth.login: username={username}")
        
        # 查找用户
        users = self.users_crud.search(username, "username")
        if not users:
            print(f"DEBUG UserAuth.login: 用户不存在 - {username}")
            return {"success": False, "message": "用户不存在"}
        
        user = users[0]
        print(f"DEBUG UserAuth.login: 找到用户，ID={user['id']}")
        
        # 验证密码
        if self._verify_password(password, user['password_hash']):
            print(f"DEBUG UserAuth.login: 密码验证成功")
            return {"success": True, "message": "登录成功", "user_id": user['id']}
        else:
            print(f"DEBUG UserAuth.login: 密码错误")
            return {"success": False, "message": "密码错误"}
    
    def get_user_info(self, user_id):
        """
        获取用户信息
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            dict: 用户信息
        """
        return self.users_crud.read(user_id)
    
    def change_password(self, user_id, old_password, new_password):
        """
        修改密码
        
        Args:
            user_id (int): 用户ID
            old_password (str): 旧密码
            new_password (str): 新密码
            
        Returns:
            dict: 修改结果
        """
        # 获取用户信息
        user = self.users_crud.read(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}
        
        # 验证旧密码
        if not self._verify_password(old_password, user['password_hash']):
            return {"success": False, "message": "旧密码错误"}
        
        # 检查新密码是否合法
        if not self._is_valid_password(new_password):
            return {"success": False, "message": "新密码不合法"}
        
        # 加密新密码并更新
        new_password_hash = self._hash_password(new_password)
        affected_rows = self.users_crud.update(user_id, password_hash=new_password_hash)
        
        return {"success": affected_rows > 0, "message": "密码修改成功" if affected_rows > 0 else "密码修改失败"}
    
    def _is_valid_username(self, username):
        """
        检查用户名是否合法（开发阶段放宽限制）
        """
        print(f"DEBUG UserAuth._is_valid_username: 检查用户名 '{username}'")
        result = (username and 
                isinstance(username, str) and 
                2 <= len(username) <= 50)  # 放宽长度限制，移除字符限制
        print(f"DEBUG UserAuth._is_valid_username: 结果={result}")
        return result
    
    def _is_valid_password(self, password):
        """
        检查密码是否合法（开发阶段放宽限制）
        """
        print(f"DEBUG UserAuth._is_valid_password: 检查密码长度={len(password) if password else 0}")
        result = password and isinstance(password, str) and 3 <= len(password) <= 200  # 放宽密码长度限制
        print(f"DEBUG UserAuth._is_valid_password: 结果={result}")
        return result
    
    def _check_user_exists(self, username):
        """
        检查用户是否存在
        """
        print(f"DEBUG UserAuth._check_user_exists: 检查用户是否存在 - {username}")
        result = len(self.users_crud.search(username, "username")) > 0
        print(f"DEBUG UserAuth._check_user_exists: 结果={result}")
        return result
    
    def _hash_password(self, password):
        """
        密码加密
        """
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password, password_hash):
        """
        验证密码
        """
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def close(self):
        """
        关闭数据库连接（使用连接池时无需手动关闭）
        """
        # 连接池会自动管理连接，无需手动关闭
        pass

def main():
    """
    测试函数
    """
    auth = UserAuth()
    
    print("=== 测试用户认证 ===")
    
    # 测试用户注册
    print("\n1. 测试用户注册:")
    register_result = auth.register("testuser1", "password123", "test1@example.com")
    print(f"注册结果: {register_result}")
    
    # 测试用户登录
    print("\n2. 测试用户登录:")
    login_result = auth.login("testuser1", "password123")
    print(f"登录结果: {login_result}")
    
    # 测试获取用户信息
    print("\n3. 测试获取用户信息:")
    if login_result["success"]:
        user_id = login_result["user_id"]
        user_info = auth.get_user_info(user_id)
        print(f"用户信息: {user_info}")
    
    auth.close()

if __name__ == "__main__":
    main()
