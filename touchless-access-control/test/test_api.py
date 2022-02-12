import requests
for i in range(11,15):
    res = requests.post('http://localhost:5000/api/addkey', json={"id":i, "value": "qwerty"+str(i), "lockid":2})
    if res.ok:
        print(res.json())
