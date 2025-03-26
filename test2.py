import requests

url = "https://tripadvisor-scraper.p.rapidapi.com/hotels/list"

querystring = {"query":"new york","page":"1"}

headers = {
	"x-rapidapi-key": "00c4aad806msh8e00931585a4552p1cba4fjsn25893b3ff1c5",
	"x-rapidapi-host": "tripadvisor-scraper.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())