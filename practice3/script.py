# thanks to https://github.com/afakeman

import urllib.request
import urllib.error
import http.cookiejar
import csv
from html.parser import HTMLParser


cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


DATA_TYPES = [
    'Temp_mean_Temp_min_Temp_max',
    'Slp_mean_Slp_min_Slp_max',
    'Oxyg_mean_Oxyg_min_Oxyg_max',
    'Hum_mean_Hum_min_Hum_max',
    'Wind_mean_Wind_min_Wind_max',
    'Soil_mean_Soil_min_Soil_max',
    'Obl_mean_Obl_min_Obl_max',
]


DATA_TYPE_CHOICES = [
    'Temperature',
    'Athmospheric pressure',
    'Oxygen content',
    'Humidity',
    'Wind',
    'soil???',
    'obl???',
]

DEFAULT_FILENAMES = [
    'temp.csv',
    'slp.csv',
    'oxyg.csv',
    'hum.csv',
    'wind.csv',
    'soil.csv',
    'obl.csv',
]


class CitySelectParser(HTMLParser):
    SELECT_ID = "id_select_town"

    def __init__(self):
        super(CitySelectParser, self).__init__()
        self.cities = []
        self.pending_option = None
        self.inside_option = False  # No nested options
        self.inside_select_town = False  # No nested selects
    
    def handle_starttag(self, tag, attrs):
        attrs = {key: value for key, value in attrs}
        if tag == 'select' and attrs['id'] == self.SELECT_ID:
            self.inside_select_town = True
        elif tag == 'option' and self.inside_select_town:
            self.inside_option = True
            value = attrs["value"].split('_')
            assert(self.pending_option is None)
            self.pending_option = value

    def handle_endtag(self, tag):
        if tag == 'select' and self.inside_select_town:
            self.inside_select_town = False
        elif tag == 'option' and self.inside_option:
            self.inside_option = False

    def handle_data(self, data):
        if self.inside_option:
            self.cities.append((data, self.pending_option[0], 
                self.pending_option[1]))
            self.pending_option = None


def fetch_available_cities():
    DATA_URL = "http://www.atlas-yakutia.ru/weather/wind/stat_weather_27612_wind.php"
    response = opener.open(DATA_URL)
    parser = CitySelectParser()
    parser.feed(response.read().decode("UTF-8", "ignore"))
    return parser.cities


def fetch_weather_data(data_type, wmo, city):
    DATA_URL = "http://www.atlas-yakutia.ru/weather/load_js_2018.php"

    # These parameters are not expected to change, so they are made constant
    POST_DATA_FIELD = 'psd'
    USER_AGENT = 'mozilla/5.0 (macintosh; intel mac os x 10_13_6) applewebkit/537.36 (khtml, like gecko) chrome/68.0.3440.84 safari/537.36'
    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 1080
    COLOR_DEPTH = 24

    HEADERS = {
        'User-Agent': 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like'\
        'Gecko) Chrome/68.0.3440.84 Safari/537.36',
    }

    request_data = "{}={},{},1965,2017,{},{},{},{},{}".format(POST_DATA_FIELD, wmo, data_type, SCREEN_WIDTH,
            SCREEN_HEIGHT, USER_AGENT, COLOR_DEPTH, city)
    req = urllib.request.Request(DATA_URL, data=request_data.encode('UTF-8'), headers=HEADERS)
    response = opener.open(req)
    return response


def fetch_session_cookie():
    # Fun fact: ver parameter is chosen by Math.Random on the website
    DATA_URL = 'http://www.atlas-yakutia.ru/antfl/ios_rab.php?ver=0.5949458969200663'
    opener.open(DATA_URL)


def user_choice(choices, prompt):
    for idx, choice in enumerate(choices):
        print("{}: {}".format(idx + 1, choice))
    chosen = None
    while chosen is None:
        try:
            chosen = int(input(prompt)) - 1
        except ValueError:
            chosen = None
    return chosen


def maybe_float(string):
    if string == '':
        return None
    else:
        return float(string)


def data_to_csv(data, filename='out.csv'):
    year = None
    month = None
    day = None
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Year', 'Month', 'Day', 'Mean', 'Min', 'Max'])
        for symbol in data.split(','):
            if ';' not in symbol:  # Must be year/month/day marker
                num = int(symbol)
                if num > 1000:  # Year marker
                    year = num
                elif 800 < num < 900:  # Month marker
                    month = num - 800  # Months start from 1
                elif 900 < num < 1000:  # Day marker
                    day = num - 900
            else:
                mean_min_max = symbol.split(';')
                mean_val = maybe_float(mean_min_max[0])
                min_val = maybe_float(mean_min_max[1])
                max_val = maybe_float(mean_min_max[2])
                writer.writerow([year, month, day, mean_val, min_val, max_val])


def main():
    print('Setting session cookie for api access...')
    try:
        fetch_session_cookie()
    except urllib.error.HTTPError:
        print('Could not fetch the cookie :(')
        exit(1)
    print('Set the session cookie')
    print('Fetching available cities...')
    try:
        cities = fetch_available_cities()
    except urllib.error.HTTPError:
        print('Could not fetch cities :(')
        exit(1)
    city_choices = map(lambda x: x[0], cities)
    idx = user_choice(city_choices, "Pick a city: ")
    city_wmo = cities[idx][2]
    city_name = cities[idx][1]
    idx = user_choice(DATA_TYPE_CHOICES, "Pick data type: ")
    data_type = DATA_TYPES[idx]
    print('Fetching weather data...')
    try:
        response = fetch_weather_data(data_type, city_wmo, city_name)
    except urllib.error.HTTPError:
        print('Could not fetch the weather data :(')
        exit(1)
    default_filename = DEFAULT_FILENAMES[idx]
    filename = input("Pick output file name [{}]: ".format(default_filename))
    if filename == '':
        filename = default_filename
    data_to_csv(response.read().decode('UTF-8', 'ignore'), filename=filename)
    print("Saved data to {}".format(filename))

if __name__ == "__main__":
    main()
