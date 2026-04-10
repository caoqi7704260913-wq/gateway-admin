#标准的验证器
class ValidationManager:
    def __init__(self):
        """
        初始化验证管理器，创建一个空的验证器列表
        """
        self.validators = []
    def add_validator(self, validator):
        """
        向验证管理器中添加一个验证器
        参数:
            validator: 要添加的验证器对象
        """
        self.validators.append(validator)   
    def validate(self, data):
        for validator in self.validators:
            result = validator.validate(data)
            if not result["success"]:
                return result
        return {"success": True, "message": "Validation passed"}
    def remove_validator(self, validator):

        """从验证器列表中移除指定的验证器
        
        Args:
            validator: 需要被移除的验证器对象
        """
        self.validators.remove(validator)      # 调用列表的remove方法移除指定的验证器
    def clear_validators(self):        self.validators.clear()  

    def has_validator(self, validator):
        return validator in self.validators 
    
    def get_validators(self):
        return self.validators  
    def set_validators(self, validators):
        self.validators = validators
        return self.validators  
    def count_validators(self):        return len(self.validators)  
    def __str__(self):
        return f"Validators: {[validator.__name__ for validator in self.validators]}"
    def __repr__(self):
        return str(self)
    def __len__(self):
        return len(self.validators)

    def __iter__(self):

        """
        返回一个迭代器对象，用于遍历验证器列表
        
        返回:
            iter: 验证器列表的迭代器
        """
        return iter(self.validators)  # 使用内置的iter函数返回验证器列表的迭代器

    def __contains__(self, item):
        return item in self.validators

    def __eq__(self, other):
        return self.validators == other.validators
    
    def __ne__(self, other):
        return not self.__eq__(other)   
    def __getitem__(self, index):
        return self.validators[index]   
    def __setitem__(self, index, value):
        self.validators[index] = value  
    def __delitem__(self, index):
        del self.validators[index]
    def __add__(self, other):
        if isinstance(other, ValidationManager):
            new_manager = ValidationManager()
            new_manager.validators = self.validators + other.validators
            return new_manager
        return NotImplemented   
    def __iadd__(self, other):
        if isinstance(other, ValidationManager):
            self.validators += other.validators
            return self
        return NotImplemented
    

    def __sub__(self, other):
        if isinstance(other, ValidationManager):
            new_manager = ValidationManager()
            new_manager.validators = [v for v in self.validators if v not in other.validators]
            return new_manager
        return NotImplemented
    def __isub__(self, other):
        if isinstance(other, ValidationManager):
            self.validators = [v for v in self.validators if v not in other.validators]
            return self
        return NotImplemented
    
    def __mul__(self, other):
        if isinstance(other, ValidationManager):
            new_manager = ValidationManager()
            new_manager.validators = [v for v in self.validators if v in other.validators]
            return new_manager
        return NotImplemented
    
    def __imul__(self, other):
        if isinstance(other, ValidationManager):
            self.validators = [v for v in self.validators if v in other.validators]
            return self
        return NotImplemented
    
    def __rmul__(self, other):
        if isinstance(other, int):
            new_manager = ValidationManager()
            new_manager.validators = self.validators * other
            return new_manager
        return NotImplemented