import requests

url = "https://sky-scanner3.p.rapidapi.com/flights/search-one-way"

querystring = {"fromEntityId":"PARI","cabinClass":"economy"}

headers = {
	"x-rapidapi-key": "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5",
	"x-rapidapi-host": "sky-scanner3.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())