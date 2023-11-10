import os
import openai
import re
import json
from flask import Flask, redirect, render_template, request, url_for, jsonify
import database_connector as connector
from openai.error import Timeout, APIConnectionError, RateLimitError

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = "https://api.openai-proxy.com/v1" 


# 指定浏览器渲染的文件类型，和解码格式
app.config['JSON_AS_ASCII'] = False


@app.route("/api", methods=["GET", "POST"])
def handle_request():
    if request.method == "POST":
        data = request.get_json()
        question = data.get("question")
        if question:
            result = test_pipeline(question)
            return jsonify({"code":200, "result": result})
    return jsonify({"error": "Question missing"})



def call_openai(content, system_message=None):
    messages = (
        [
            {"role": "system", "content": system_message},
        ]
        if system_message != None
        else []
    )
    messages.append({"role": "user", "content": content})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,
        )
    except Exception as e:
        raise e
    return response.choices[0].message["content"]



def benchmark_query(question):
    """
    The input is the user's query, and the output is a user-friendly answer. 
    During this process, two calls to OpenAI are made, 
    and exceptions that may occur during the calls need to be considered.
    """
    s_content, sys_msg = wrap_text_to_sql_prompt(question)
    sql = call_openai(s_content, sys_msg)
    
    sql_res = execute_sql_query(sql)
    
    if isinstance(sql_res, str):
        return "Failure"

    a_content = wrap_final_answer_prompt(question, sql_res)
    a_res = call_openai(a_content)
    return a_res



def extract_sql_query(text):
    text = text.rstrip(';')
    pattern = r"SELECT\s+.+\s+FROM\s+.+"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return match.group(0)
    else:
        return None



def test_pipeline(question):
    print(question)
    print(app.answers)

    # 请求的时候看到答案已经访问过了就不 call openai
    cached_ans = lookup_cache(question)
    if cached_ans:
        return cached_ans
    
    # 根据问题生成输入内容
    input_content, sys_msg = wrap_test_prompt(question)

    # 调用 OpenAI API 执行 SQL 查询
    try:
        sql_query = call_openai(input_content, sys_msg)
        print(sql_query)
        sql_query = extract_sql_query(sql_query)
        print(sql_query)
    except (Timeout, RateLimitError, APIConnectionError) as e:
        print("Call API Error:")
        print(e)
        sql_query = costom_sql()
        print("Use default SQL command: ", sql_query)

    # 创建数据库连接器并连接到数据库
    db_connector = connector.MySQLConnector("db11")
    
    db_connector.connect()

    # 执行 SQL 查询并获取结果
    try:
        sql_result = db_connector.execute_query(sql_query)
    except Exception as e:
        # 如果SQL执行出错，执行默认的SQL语句
        print("Run SQL command Error:")
        print(e)
        default_sql_query = costom_sql()
        print("Use default SQL command: ", default_sql_query)
        sql_result = db_connector.execute_query(default_sql_query)
    
    print(sql_result)

    # 关闭数据库连接
    db_connector.close()

    # 根据问题和 SQL 结果生成最终回答的输入内容
    final_answer_content = wrap_final_answer_prompt(question, sql_result)

    # 调用 OpenAI API 获取最终回答
    try:
        final_answer = call_openai(final_answer_content)
    except (Timeout, RateLimitError, APIConnectionError) as e:
        print("Call API Error:")
        print(e)
        final_answer = costom_res()
    
    print(final_answer)

    return final_answer



def wrap_final_answer_prompt(question, sql_res):
    """
    Combining the original user query with the results obtained from the database,
    provide a user-friendly response in a conversational manner.
    """
    return """
Based on the question : 【```{question}```】. \
the database query result ```{sql_res}```. 

Now based on the above messages, give me a user-friendly response in Chinese to help me know the results. \
Make sure the response is easy to understand.
""".format(
        question=question, sql_res=sql_res
    )



def wrap_test_prompt(question):
    system_message = """
You are a MySQL database expert. \
Your task is to provide a SQL query code based on the user's request, \
so that the user can obtain the necessary information from the database.

User requests are separated by ``` as a delimiter. \
You are supposed to return SQL code directly based on user's requirements. \
You must ensure that the result contains only SQL code, without any additional content. \
The code should retrieve only the information that user needs.

Background knowledge: \
The table is created with the following statement:
CREATE TABLE `ETTh1` (
  `date` varchar(255) DEFAULT NULL,
  `HUFL` varchar(255) DEFAULT NULL,
  `HULL` varchar(255) DEFAULT NULL,
  `MUFL` varchar(255) DEFAULT NULL,
  `MULL` varchar(255) DEFAULT NULL,
  `LUFL` varchar(255) DEFAULT NULL,
  `LULL` varchar(255) DEFAULT NULL,
  `OT` varchar(255) DEFAULT NULL
) \

If the user's request doesn't contain any explicit query steps, \
please return the following SQL query code as the default result: \
"SELECT * FROM ETTh1 LIMIT 1";

Return your answer in the format as following:
SELECT ..... FROM .....
"""
    return "User request: ```{}```".format(question), system_message



def wrap_text_to_sql_prompt(question):
    """
    Transforming the user's query into an executable SQL statement.
    """
    system_message = """
You are a MySQL database expert. \
Your task is to provide a SQL query code based on the user's request, \
so that the user can obtain the necessary information from the database.

User requests are separated by ``` as a delimiter. \
You are supposed to return SQL code directly based on user's requirements. \
You must ensure that the result contains only SQL code, without any additional content. \
The code should retrieve only the information that user needs.

Background knowledge: \
The table is created with the following statement:
CREATE TABLE `forecast_result` (
    `model_name` VARCHAR(255) DEFAULT NULL,
    `strategy_args` VARCHAR(255) DEFAULT NULL,
    `model_params` VARCHAR(255) DEFAULT NULL,
    `mae` DOUBLE DEFAULT NULL,
    `mse` DOUBLE DEFAULT NULL,
    `rmse` DOUBLE DEFAULT NULL,
    `mape` DOUBLE DEFAULT NULL,
    `smape` DOUBLE DEFAULT NULL,
    `mase` DOUBLE DEFAULT NULL,
    `file_name` VARCHAR(255) DEFAULT NULL,
    `fit_time` DOUBLE DEFAULT NULL,
    `inference_time` DOUBLE DEFAULT NULL
) \

if the user's request doesn't contain any explicit query steps, \
please return the following SQL query code as the default result: \
SELECT * FROM forecast_result LIMIT 1;

Return your answer in the format as following:
SELECT ..... FROM .....
"""
    return "User request: ```{}```".format(question), system_message


# if __name__ == "__main__":
#     app.run(debug=True)

def costom_sql():
    return "SELECT * FROM ETTh1 LIMIT 1;"


def costom_res():
    return "这里是事先写好的默认输出"


def lookup_cache(question):
    if question in app.answers:
        return app.answers[question]
    return None


def load_local_answers():
    answer_file = "answer.json"
    print(f"Load local answers {answer_file}...")

    if not os.path.exists(answer_file):
        app.answers = {}
    else:
        with open(answer_file, "r", encoding='utf-8') as f:
            data = json.loads(f.read())
        answer_dict = {item["question"]: item["result"] for item in data}
        app.answers = answer_dict
    print(f"Local Answers Count: {len(app.answers)}")


if __name__ == "__main__":
    with app.app_context():
        load_local_answers()
    app.run(debug=True)
