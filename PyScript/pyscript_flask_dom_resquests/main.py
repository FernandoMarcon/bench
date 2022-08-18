from random import randint

from flask import (
    Flask,
    render_template,
    jsonify,
    request
)

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def index():
    if request.is_json:
        if request.method == 'GET':
            number = randint(1, 10)
            return jsonify({'number':number})
        if request.method == "POST":
            text = float(request.data)
            new_text = f"I got: {text}"
            return jsonify({'data': new_text})

    return render_template('index.html')

if __name__=="__main__":
    app.run()