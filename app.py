import os

import openai
from flask import Flask, redirect, render_template, request, url_for
import psycopg2

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = "https://api.openai-proxy.com/v1" 



@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        question = request.form["animal"]
        prompt = generate_prompt(question)
        messages = [{"role": "user", "content": prompt}]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,  # this is the degree of randomness of the model's output
        )
        return redirect(url_for("index", result=response.choices[0].message["content"]))

    result = request.args.get("result")
    print(result)
    return render_template("index.html", result=result)



def generate_prompt(question):
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

# TODO
def execute_response_stmt(stmt):
    conn = psycopg2.connect(
        host="localhost",
        port="5432",
        database="your_database",
        user="your_username",
        password="your_password"
    )

    # Execute the stmt
    with conn.cursor() as cursor:
        cursor.execute(response)
        result = cursor.fetchall()
        print(result)

    conn.close()
        