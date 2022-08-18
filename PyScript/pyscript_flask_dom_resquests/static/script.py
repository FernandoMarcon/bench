import pyodide
from pyodide.http import pyfetch

def on_click(e):
    left_ul = document.getElementById('left')
    left_ul.innerHTML = 'Hello World'

async def make_request(url, method, body=None, headers=None):
    if not headers:
        headers = {
            'X-Requested-With':'XMLHttpRequest',
            'Content-Type':'application/json'
        }
    
    response = await pyfetch(
        url=url,
        method=method,
        body=body,
        headers=headers
    )

    return await response.json()

async def get_number_onclick(e):
    data = await make_request(url='/', method='GET')
    ul = document.querySelector('#left')
    li = document.createElement('li')
    li.innerHTML = data['number']

    li.addEventListener('click', pyodide.create_proxy(send_number_onclick))

    ul.appendChild(li)


async def send_number_onclick(e):
    number = e.target.innerHTML

    data = await make_request(url='/', method='POST', body=number)
    ul = document.querySelector('#right')
    li = document.createElement('li')
    li.innerHTML = data['data']

    ul.appendChild(li)

def main():
    button = document.getElementById('button')
    button.addEventListener('click', pyodide.create_proxy(on_click))

    red_button = document.querySelector('#red-button')
    red_button.addEventListener('click', pyodide.create_proxy(get_number_onclick))



main()