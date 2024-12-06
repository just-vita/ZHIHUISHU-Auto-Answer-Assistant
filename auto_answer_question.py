import logging
import random
import time

import os

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from cnocr import CnOcr
from selenium import webdriver
from selenium.webdriver.common.by import By

from model import get_model

# 设置日志级别为WARNING，这样ERROR级别的日志将不会被打印
logging.getLogger('selenium').setLevel(logging.WARNING)

ocr = CnOcr()

# 初始化模型
model = get_model()


def error_handler(func):
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"函数 {func.__name__} 发生错误: {e}")
                input("请修复错误并按回车键继续...")

    return wrapper


def get_driver(url):
    options = webdriver.ChromeOptions()
    # selenium尝试连接https网站时会报SSL handshake failed, 加上以下两行代码可以忽略证书错误
    options.add_argument('--ignore-certificate-errors')
    # 设置日志级别为3, 仅记录警告和错误
    options.add_argument('--log-level=3')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(random.uniform(0.5, 2))
    return driver


def get_test_num(driver):
    # 调整为新网站的题目列表获取方式
    test_list = driver.find_elements(By.CLASS_NAME, 'singleQuesId')
    return len(test_list)


def text_orc(image='question.png'):
    ocr_results = ocr.ocr(image)
    # 提取文本内容
    extracted_text = '\n'.join([item['text'] for item in ocr_results if item['text'].strip()])
    return extracted_text


def get_answer(question):
    prompt = f"""
请仔细阅读以下题目并思考分析，根据题目类型，严格按照以下要求作答：

选择题（单选）： 如果题目为单选题，请从选项中选择一个正确的答案，并仅输出该选项（A、B、C或D），不提供任何额外解释。
选择题（多选）： 如果题目为多选题，请选择所有正确的选项，并仅输出所有正确选项的字母，用','分隔（如A,C），按字母顺序排列，不提供任何额外解释。
判断题： 如果题目为判断题，请分析题目并仅输出 "对" 或 "错"，不提供任何额外解释。
请遵循以上规则直接给出你的答案。

题目：
{question}

你的答案："""
    answer_list = []
    index = 0
    while True:
        cur_answer = model.get_response(prompt)
        print(f'大模型第{index + 1}次输出：{cur_answer}')
        if cur_answer in answer_list:
            return cur_answer
        answer_list.append(cur_answer)
        index += 1


@error_handler
def answer(driver, index):
    # 根据新网站的HTML结构调整
    question_elements = driver.find_elements(By.CLASS_NAME, 'TiMu')
    question_element = question_elements[index]

    # 截图并识别题目
    question_element.screenshot('question.png')
    question_str = text_orc()
    print(f'第{index + 1}题：{question_str}')

    # 获取答案
    answer = get_answer(question_str)
    print(f'最终答案：{answer}')

    # 选择题处理
    choice_elements = question_element.find_elements(By.CLASS_NAME, 'before-after')

    # 判断题型（单选或多选）
    check_box = question_element.find_elements(By.CLASS_NAME, 'before-after-checkbox')
    is_multiple = False
    if check_box:
        is_multiple = True
        choice_elements = check_box

    if is_multiple:  # 多选题
        answer_indices = [ord(a) - ord('A') for a in answer.split(',')]
        for index in answer_indices:
            choice_elements[index].click()
            time.sleep(random.uniform(0.2, 0.5))
    elif answer == '对' or answer == '错':  # 单选题
        for choice_element in choice_elements:
            if choice_element.text[-1:] == answer:
                choice_element.click()
                time.sleep(random.uniform(0.2, 0.5))
    else:
        answer_index = ord(answer) - ord('A')
        choice_elements[answer_index].click()
        time.sleep(random.uniform(0.2, 0.5))


def auto_answer(driver):
    driver.switch_to.default_content()
    driver.switch_to.frame('iframe')
    driver.switch_to.frame(0)
    driver.switch_to.frame('frame_content')
    total_questions = get_test_num(driver)
    for index in range(total_questions):
        answer(driver, index)

        # 如果是最后一题，点击提交
        if index == total_questions - 1:
            submit_button = driver.find_element(By.CLASS_NAME, 'btnSubmit')
            submit_button.click()
            time.sleep(random.uniform(1, 2))

            # 确认提交弹窗
            driver.switch_to.default_content()
            driver.find_element(By.XPATH, '//*[@id="popok"]').click()

            print("提交成功")
            return


def handle_driver(driver):
    # 章节测验 class：TestTitle_name
    # 任务点未完成 class：ans-job-icon
    # 任务点已完成 class：ans-job-icon-clear
    # 下一节 id：prevNextFocusNext

    while True:
        driver.switch_to.default_content()

        next_btn = driver.find_element(By.ID, 'prevNextFocusNext')
        if next_btn is None:
            print("已经是最后一节，结束")
            break
        driver.switch_to.frame('iframe')

        try:
            icon = driver.find_element(By.CLASS_NAME, 'ans-job-icon')
            if icon.get_attribute("aria-label") == '任务点已完成':
                print("当前任务点已完成")
                driver.switch_to.default_content()
                next_btn.click()
                time.sleep(2)
                continue
        except:
            pass

        print("当前任务点未完成")

        try:
            driver.switch_to.frame(0)
            driver.switch_to.frame('frame_content')
        except Exception:
            print("当前页面不是测验页面")
            driver.switch_to.default_content()
            next_btn.click()
            time.sleep(2)
            continue
        print("当前页面是测验页面")

        auto_answer(driver)
        time.sleep(2)


def main(url):
    driver = get_driver(url)
    input("请登录并进入测试页面后按回车继续...")
    handle_driver(driver)
    input("请按任意键退出...")
    driver.quit()


if __name__ == '__main__':
    # url = input("请输入页面链接：")
    url = "你的网课url"
    main(url)
