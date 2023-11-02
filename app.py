import os

import openai
from flask import Flask, redirect, render_template, request, url_for, jsonify
import psycopg2

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = "https://api.openai-proxy.com/v1" 


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        question = request.form["animal"]
        prompt = wrap_text_to_sql_prompt(question)
        return redirect(url_for("index", result=call_openai(prompt)))

    result = request.args.get("result")
    return render_template("index.html", result=result)


@app.route("/api", methods=["POST"])
def handle_request():
    data = request.get_json()
    question = data.get("question")
    if question:
        prompt = wrap_text_to_sql_prompt(question)
        sql_query = call_openai(prompt)
        return jsonify({"sql_query": sql_query})
    return jsonify({"error": "Question missing"})


def call_openai(content):
    messages = [{"role": "user", "content": content}]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,  
    )
    return response.choices[0].message["content"]


def benchmark_query(question):
    """
    The input is the user's query, and the output is a user-friendly answer. 
    During this process, two calls to OpenAI are made, 
    and exceptions that may occur during the calls need to be considered.
    """
    s_content = wrap_text_to_sql_prompt(question)
    sql = call_openai(s_content)
    
    sql_res = execute_sql_query(sql)
    
    if isinstance(sql_res, str):
        return "Failure"

    a_content = generate_prompt_user(question, sql_res)
    a_res = call_openai(a_content)
    return a_res
    
    
    
def wrap_final_answer_prompt(question, sql_res):
    """
    Combining the original user query with the results obtained from the database, 
    provide a user-friendly response in a conversational manner.
    """
    pass



def wrap_text_to_sql_prompt(question):
    """
    Transforming the user's query into an executable SQL statement.
    """
    return """
你是一位 PostgreSQL 数据库专家.
用户请求以 ```作为分隔符, \
你的任务是根据用户请求返回一段SQL查询代码, \
使得用户可以使用这段查询代码从数据库中获得需要的信息.

你只需要返回SQL代码, \
且根据用户需求, 使得代码只返回用户需要的信息.

前置知识：\
1. 数据库表名为forecast_result。
2. 这张表的结构是 (model_name, strategy_args, \
model_params, mae, mse, rmse, mape, smape, mase, \
file_name, fit_time, inference_time).

如果用户请求中没有明确的查询步骤，\
请直接返回以下SQL查询代码作为默认结果: \
SELECT * FROM forecast_result LIMIT 1;

用户请求: ```{}```
""".format(question)


def execute_sql_query(sql_query):
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="your_database",
            user="your_username",
            password="your_password"
        )

        with conn.cursor() as cursor:
            cursor.execute(sql_query)
            result = cursor.fetchall()
            return result
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)
