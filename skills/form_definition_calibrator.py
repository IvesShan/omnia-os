"""
Omnia Skill: Form Definition & Calibrator
Version: 1.0.0
Author: Aether
Purpose:
    将原始表单数据（来自网页抓取或OCR）解析、清洗、转化为标准的
    FormField 和 FormDefinition 对象。校准字段类型、标签、默认值和约束。
    此技能服务于所有UI层（Web, CLI, API），是“表单”的核心逻辑。

Dependencies:
    - pydantic
    - re

Input Schema:
    {
      "raw_data": "string | list[dict]",
      "source_type": "html_string | ocr_text | json_list",
      "title": "optional[string]",
      "form_id": "optional[string]"
    }

Output Schema:
    {
      "status": "success | failure",
      "form_definition": "FormDefinition | null",
      "message": "string"
    }
"""

from typing import List, Dict, Optional, Any, Union
import re
import json

# --- Pydantic 模型定义 ---
# 这些是Omnia表单系统的核心数据结构
# 它们定义了字段的“是什么”和“能做什么”，而不是“怎么画”

class FieldOption(BaseModel):
    """字段选项，用于下拉框、单选、多选"""
    label: str
    value: str
    
class FieldValidation(BaseModel):
    """字段验证规则"""
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # 正则表达式
    min_value: Optional[float] = None
    max_value: Optional[float] = None

class FormField(BaseModel):
    """表单单个字段的定义"""
    id: str
    label: str
    type: str = 'text'  # text, email, password, number, select, checkbox, radio, date, time, file, hidden, etc.
    required: bool = False
    placeholder: Optional[str] = None
    default_value: Any = None
    options: Optional[List[FieldOption]] = None
    validation: Optional[FieldValidation] = None
    help_text: Optional[str] = None
    # 扩展属性，用于存放非标准或特定UI框架的属性
    meta: Dict[str, Any] = {}

class FormDefinition(BaseModel):
    """整个表单的定义"""
    id: str
    title: str
    description: Optional[str] = None
    version: str = '1.0.0'
    fields: List[FormField] = []
    submit_button_text: str = '提交'
    submit_api_url: Optional[str] = None  # 提交到哪个API

# --- 真正的技能逻辑 ---

import re

class FormDefinitionCalibrator:
    """
    表单定义校准器。
    负责从混乱的源数据中提取出结构化的 FormDefinition。
    """

    def __init__(self, raw_data: Union[str, List[Dict]], source_type: str):
        self.raw_data = raw_data
        self.source_type = source_type

    def calibrate(self, title: Optional[str] = None, form_id: Optional[str] = None) -> Dict:
        """
        执行校准。
        """
        if self.source_type == 'json_list':
            return self._calibrate_from_json_list(title, form_id)
        elif self.source_type == 'html_string':
            # 简化版 HTML 解析逻辑
            return {"status": "failure", "form_definition": None, "message": "HTML 解析尚未实现"}
        elif self.source_type == 'ocr_text':
            # 简化版 OCR 解析逻辑
            return {"status": "failure", "form_definition": None, "message": "OCR 解析尚未实现"}
        else:
            return {"status": "failure", "form_definition": None, "message": f"不支持的来源类型: {self.source_type}"}

    def _calibrate_from_json_list(self, title: Optional[str], form_id: Optional[str]) -> Dict:
        """
        从 JSON 列表（通常是抓包或API响应）校准。
        """
        if not isinstance(self.raw_data, list):
            try:
                # 尝试解析字符串
                data_list = json.loads(self.raw_data)
            except (json.JSONDecodeError, TypeError):
                return {"status": "failure", "form_definition": None, "message": "无法解析 JSON 数据"}
        else:
            data_list = self.raw_data
        
        if not data_list:
            return {"status": "failure", "form_definition": None, "message": "输入数据为空"}

        fields = []
        for i, item in enumerate(data_list):
            if not isinstance(item, dict):
                continue
            
            # 提取基础信息
            field_id = item.get('id', item.get('name', f'field_{i}'))
            label = item.get('label', item.get('title', field_id))
            field_type = self._infer_type(item)
            required = item.get('required', item.get('is_mandatory', False))
            placeholder = item.get('placeholder', item.get('hint', ''))
            default = item.get('default_value', item.get('default', None))
            help_text = item.get('help_text', item.get('description', ''))

            # 提取选项
            options = []
            if field_type in ['select', 'radio', 'checkbox']:
                raw_options = item.get('options', item.get('items', item.get('choices', [])))
                for opt in raw_options:
                    if isinstance(opt, dict):
                        # 假设 {label: ..., value: ...} 或 {text: ..., val: ...}
                        opt_label = opt.get('label', opt.get('text', opt.get('name', str(opt.get('value')))))
                        opt_value = opt.get('value', opt.get('val', opt_label))
                        options.append(FieldOption(label=str(opt_label), value=str(opt_value)))
                    elif isinstance(opt, str):
                        options.append(FieldOption(label=opt, value=opt))

            # 构建验证规则
            validation = FieldValidation(
                min_length=item.get('min_length', item.get('minlength')),
                max_length=item.get('max_length', item.get('maxlength')),
                pattern=item.get('pattern', item.get('regex')),
                min_value=item.get('min_value', item.get('min')),
                max_value=item.get('max_value', item.get('max'))
            )
            # 如果所有验证字段都是 None，则不包含 validation 对象
            if all(v is None for v in validation.model_dump().values()):
                validation = None

            fields.append(FormField(
                id=str(field_id),
                label=str(label),
                type=field_type,
                required=bool(required),
                placeholder=str(placeholder),
                default_value=default,
                options=options if options else None,
                validation=validation,
                help_text=str(help_text),
                meta={k: v for k, v in item.items() if k not in [
                    'id', 'name', 'label', 'title', 'type', 'field_type', 'required', 'is_mandatory',
                    'placeholder', 'hint', 'default_value', 'default', 'help_text', 'description',
                    'options', 'items', 'choices', 'min_length', 'minlength', 'max_length', 'maxlength',
                    'pattern', 'regex', 'min_value', 'min', 'max_value', 'max'
                ]}
            ))

        form_id = form_id or f'form_{int(datetime.now().timestamp())}'
        form_title = title or '导入的表单'

        definition = FormDefinition(
            id=form_id,
            title=form_title,
            fields=fields
        )

        return {"status": "success", "form_definition": definition.model_dump(), "message": f"成功解析 {len(fields)} 个字段"}

    def _infer_type(self, item: Dict) -> str:
        """根据字典内容推断字段类型"""
        if 'type' in item:
            return item['type']
        if 'field_type' in item:
            return item['field_type']
        
        has_options = any(k in item for k in ['options', 'items', 'choices'])
        if has_options:
            # 简单判断，有选项默认为 select
            return 'select'

        return 'text'

# --- 技能入口点 (供 Omnia Skill Manager 调用) ---

def run_skill(input_data: Dict) -> Dict:
    """
    标准技能入口函数。
    """
    try:
        raw_data = input_data.get('raw_data')
        source_type = input_data.get('source_type', 'json_list')
        title = input_data.get('title')
        form_id = input_data.get('form_id')

        if not raw_data:
            return {"status": "failure", "form_definition": None, "message": "缺少 raw_data 参数"}

        calibrator = FormDefinitionCalibrator(raw_data, source_type)
        return calibrator.calibrate(title, form_id)

    except Exception as e:
        # 捕获所有未知错误
        # import traceback
        # traceback.print_exc() # 记录到日志
        return {"status": "failure", "form_definition": None, "message": f"技能执行失败: {str(e)}"}

# 自测代码
if __name__ == '__main__':
    test_data = [
        {"name": "username", "label": "用户名", "required": True, "min_length": 3, "hint": "请输入您的登录名"},
        {"name": "email", "label": "邮箱", "type": "email", "required": True},
        {"name": "age", "label": "年龄", "type": "number", "min": 0, "max": 150, "default": 18},
        {"name": "fav_color", "label": "喜欢的颜色", "options": ["红", "绿", "蓝"]},
        {"name": "city", "label": "城市", "options": [{"text": "北京", "val": "beijing"}, {"text": "上海", "val": "shanghai"}]}
    ]
    
    # 模拟调用
    result = run_skill({
        "raw_data": test_data,
        "source_type": "json_list",
        "title": "用户注册表单 (自测)"
    })
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
