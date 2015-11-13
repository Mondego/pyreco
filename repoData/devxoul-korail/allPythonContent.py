__FILENAME__ = korail
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests


class Train(object):

    #: 기차 종류
    #: 00: KTX
    #: 01: 새마을호
    #: 02: 무궁화호
    #: 03: 통근열차
    #: 04: 누리로
    #: 05: 전체 (검색시에만 사용)
    #: 06: 공학직통
    #: 07: KTX-산천
    #: 09: ITX-청춘
    train_type = None

    #: 출발역 코드
    dep_code = None

    #: 출발날짜 (yyyyMMdd)
    dep_date = None

    #: 출발시각 (hhmmss)
    dep_time = None

    #: 도착역 코드
    arr_code = None

    #: 도착 시각
    arr_time = None

    #: 인원
    count = 0

    #: 특실 예약가능 여부
    first_class = False

    #: 일반실 예약가능 여부
    general_admission = False

    def __repr__(self):
        return '[%s] %s~%s(%s~%s) [특실:%d][일반실:%d]' % (
            self.train_type.encode('utf-8'),
            self.dep_code.encode('utf-8'),
            self.dep_time.encode('utf-8'),
            self.arr_code.encode('utf-8'),
            self.arr_time.encode('utf-8'),
            self.first_class,
            self.general_admission,
        )


class Korail(object):

    #: A `requests` session.
    session = requests.session()

    def __init__(self):
        self.session.headers["User-Agent"] = \
            "Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1)"

    def all_stations(self):
        """Load all stations from Korail server. Recommend using static json
        file instead.
        """
        stations = []
        for i in range(14):
            url = 'http://www.korail.com/servlets/pr.pr11100.sw_pr11111_f1Svt'
            params = {
                'hidKorInx': i,  # an index for '가'~'하'
            }
            r = requests.get(url, params=params)
            html = r.text.split('<table class="s-view">')[3]
            rows = html.split("javascript:putStation('")[1:]
            for row in rows:
                name = row.split("'")[0]
                code = row.split(",'")[1].split("'")[0]
                stations.append(dict(code=code, name=name))
        return stations

    def search_station(self, query):
        """Search stations with name from `self.stations`.

        :param query: A searching query.
        """
        import stations
        return [s for s in stations.stations if query in s['name']]

    def login(self, id, password, use_phone=False):
        """Login to Korail server.

        :param id: Korail membership number or phone number. Phone number
                   should be authenticated for using phone number signing.
        :param password: A password.
        :param use_phone: `True` for use phone number signing.
        """
        url = 'https://www.korail.com/servlets/hc.hc14100.sw_hc14111_i2Svt'
        data = {
            # '2' for membership number signing
            # '4' for phone number signing
            'selInputFlg': '4' if use_phone else '2',
            'UserId': id,
            'UserPwd': password,
            'hidMemberFlg': '1',  # 없으면 입력값 오류
            'txtDv': '1' if len(password) == 4 else '2',
        }
        r = self.session.post(url, data=data)

        # if succeeded, html page shows redirect javascript code.
        if 'w_mem01106' in r.text:
            return True
        return False

    def logout(self):
        url = 'http://www.korail.com/2007/mem/mem01000/w_mem01102.jsp'
        self.session.get(url)

    def search_train(self, dep, arr, date, time='000000', train='05', count=1):
        """Search trains.

        :param dep: A departure station code.
        :param arr: An arrival station code.
        :param date: A departure date. `yyyyMMdd` formatted.
        :param time: A departure time. `hhmmss` formatted.
        :param train: A type of train.
                      - 00: KTX, KTX-산천(07)도 함께 검색됨
                      - 01: 새마을호
                      - 02: 무궁화호
                      - 03: 통근열차
                      - 04: 누리로
                      - 05: 전체 (기본값)
                      - 06: 공학직통
                      - 09: ITX-청춘
        :param count: Passengers count. Minimum is 1, maximum is 9.
        """
        url = 'http://www.korail.com/servlets/pr.pr21100.sw_pr21111_i1Svt'
        params = {
            'txtGoAbrdDt': date,
            'txtGoHour': time,
            'txtGoStartCode': dep,
            'txtGoEndCode': arr,
            'checkStnNm': 'N',
            'radJobId': '1',  # 직통
            'txtPsgCnt1': count,
            'selGoTrain': train
        }
        r = self.session.get(url, params=params)

        html = BeautifulSoup(r.text)

        # A div class 'point02' represents an error message.
        error = html.select('.point02')
        if error:
            raise KorailError(error[0].string.strip())

        rows = html.select('table.list-view tr')[1:]

        trains = []
        train_info = r.text.split('new train_info(')[1:]
        i = 0
        for info in train_info:
            obj = info.split(',')
            train = Train()
            train.train_type = obj[22].strip()[1:-1]
            train.dep_code = obj[18].strip()[1:-1]
            train.dep_date = obj[24].strip()[1:-1]
            train.dep_time = obj[25].strip()[1:-1]
            train.arr_code = obj[19].strip()[1:-1]
            train.arr_time = obj[27].strip()[1:-1]
            train.count = count

            td7s = rows[i].select('td[width=7%]')

            # https://github.com/devxoul/korail/issues/4
            if not td7s:
                break

            # 특실
            img = td7s[0].select('img')
            content = img[0] if img else td7s[0].contents[0]
            train.first_class = 'yes' in content.__str__()

            # 일반실
            img = td7s[1].select('img')
            content = img[0] if img else td7s[0].contents[0]
            train.general_admission = 'yes' in content.__str__()

            trains.append(train)
            i += 1

        return trains

    def reserve(self, train):
        """Reserve a train.

        :param train: An instance of `Train`.
        """

        # reservation server checks referer.
        self.session.headers['Referer'] = \
            'http://www.korail.com/servlets/pr.pr21100.sw_pr21111_i1Svt'
        url = 'http://www.korail.com/servlets/pr.pr12100.sw_pr12111_i1Svt'
        data = {
            'txtCompaCnt1': train.count,  # 인원
            'txtDptRsStnCd1': train.dep_code,  # 출발역 코드
            'txtDptDt1': train.dep_date,  # 출발날짜
            'txtDptTm1': train.dep_time,  # 출발시각
            'txtArvRsStnCd1': train.arr_code,  # 도착역 코드
            'txtTrnClsfCd1': train.train_type,  # 열차 종류 (Train Class Code인듯)

            # 15: 기본
            # 18: 2층석
            # 19: 유아동반
            # 19: 편한대화(중복?)
            # 21: 휠체어
            # 28: 전동휠체어
            # 29: 교통약자(없어진듯)
            # 30: 레포츠보관함
            # 31: 노트북
            # 32: 자전거거치대
            # XX: 수유실인접
            'txtSeatAttCd4': '15',
            'txtPsgTpCd1': '1',  # ??? - 단체예약, 개인예약 구분이라는데...

            # 1101: 개인예약
            # 1102: 예약대기
            # 1103: SEATMAP예약
            'txtJobId': '1101',
            'txtJrnyCnt': '1',  # 환승 횟수 (1이면 편도)

            # 1: 일반실
            # 2: 특실
            'txtPsrmClCd1': '1',
            'txtJrnySqno1': '001',  # ???
            'txtJrnyTpCd1': '11',  # 편도
        }
        r = self.session.post(url, data=data)

        # if not logged in, server returns redirect script.
        if 'w_mem01100.jsp' in r.text:
            raise KorailError("로그인이 필요합니다.")

        elif u"홈페이지주소를 잘못 입력하셨습니다." in r.text:
            raise KorailError("홈페이지주소를 잘못 입력하셨습니다. Referer를 확인해주세요.")

        elif u"20분 이내 열차는" in r.text:
            raise KorailError("20분 이내 열차는 예약하실 수 없습니다. "
                              "역창구 및 자동발매기를 이용하시기 바랍니다.")

        elif u'오류' in r.text:
            html = BeautifulSoup(r.text)
            error = html.select('.point02')
            raise KorailError(error[0].string.strip())

        elif 'w_adv03100.gif' in r.text:
            return True

        raise KorailError("Unhandled Error")

    def tickets(self):
        """Get my ticket ids.
        """
        tickets = []
        page = 1
        while True:
            url = 'http://www.korail.com/pr/pr13500/w_pr13510.jsp'
            params = dict(hidSelPage=page)
            r = self.session.get(url, params=params)
            pnrs = r.text.split("new pnr_info( '")
            if len(pnrs) < 2:
                break
            for pnr in pnrs[1:]:
                ticket_id = pnr.split("'")[0]
                tickets.append(ticket_id)
            page += 1
        return tickets

    def cancel_ticket(self, ticket_id):
        """Cancel reservation.

        :param pnr_id: A ticket id for cancelatino.
        """
        url = 'http://www.korail.com/servlets/pr.pr14500.sw_pr14514_i1Svt?'
        data = {
            'txtPnrNo': ticket_id,
            'txtLngScnt': '01',
            'txtJrnySqno': '001',
        }
        r = self.session.get(url, params=data)
        return u"정상적으로 취소가 완료되었습니다." in r.text


class KorailError(Exception):

    def __init__(self, message):
        self.message = message

########NEW FILE########
__FILENAME__ = stations
# -*- coding: utf-8 -*-

stations = [
    {
        "code": "0342",
        "name": u"가수원"
    },
    {
        "code": "0476",
        "name": u"가야"
    },
    {
        "code": "0150",
        "name": u"가평"
    },
    {
        "code": "0309",
        "name": u"각계"
    },
    {
        "code": "0172",
        "name": u"간현"
    },
    {
        "code": "0481",
        "name": u"갈촌"
    },
    {
        "code": "0028",
        "name": u"강경"
    },
    {
        "code": "0115",
        "name": u"강릉"
    },
    {
        "code": "0151",
        "name": u"강촌"
    },
    {
        "code": "0482",
        "name": u"개양"
    },
    {
        "code": "0219",
        "name": u"개태사"
    },
    {
        "code": "0160",
        "name": u"개포"
    },
    {
        "code": "0216",
        "name": u"거제"
    },
    {
        "code": "0433",
        "name": u"거촌"
    },
    {
        "code": "0184",
        "name": u"건천"
    },
    {
        "code": "0208",
        "name": u"경강"
    },
    {
        "code": "0024",
        "name": u"경산"
    },
    {
        "code": "0021",
        "name": u"경주"
    },
    {
        "code": "0468",
        "name": u"경화"
    },
    {
        "code": "0218",
        "name": u"계룡"
    },
    {
        "code": "0240",
        "name": u"고막원"
    },
    {
        "code": "0122",
        "name": u"고한"
    },
    {
        "code": "0049",
        "name": u"곡성"
    },
    {
        "code": "0259",
        "name": u"공전"
    },
    {
        "code": "0370",
        "name": u"관촌"
    },
    {
        "code": "0491",
        "name": u"광곡"
    },
    {
        "code": "0501",
        "name": u"광명"
    },
    {
        "code": "0068",
        "name": u"광양"
    },
    {
        "code": "0145",
        "name": u"광운대"
    },
    {
        "code": "0042",
        "name": u"광주"
    },
    {
        "code": "0036",
        "name": u"광주송정"
    },
    {
        "code": "0082",
        "name": u"광천"
    },
    {
        "code": "0241",
        "name": u"괴목"
    },
    {
        "code": "0050",
        "name": u"구례구"
    },
    {
        "code": "0013",
        "name": u"구미"
    },
    {
        "code": "0019",
        "name": u"구포"
    },
    {
        "code": "0329",
        "name": u"구학"
    },
    {
        "code": "0323",
        "name": u"국수"
    },
    {
        "code": "0061",
        "name": u"군북"
    },
    {
        "code": "0505",
        "name": u"군산"
    },
    {
        "code": "0043",
        "name": u"극락강"
    },
    {
        "code": "0736",
        "name": u"금강"
    },
    {
        "code": "0239",
        "name": u"금곡"
    },
    {
        "code": "0732",
        "name": u"금릉"
    },
    {
        "code": "0187",
        "name": u"기장"
    },
    {
        "code": "0246",
        "name": u"김유정"
    },
    {
        "code": "0031",
        "name": u"김제"
    },
    {
        "code": "0012",
        "name": u"김천"
    },
    {
        "code": "0507",
        "name": u"김천구미"
    },
    {
        "code": "0461",
        "name": u"나원"
    },
    {
        "code": "0201",
        "name": u"나전"
    },
    {
        "code": "0037",
        "name": u"나주"
    },
    {
        "code": "0164",
        "name": u"나한정"
    },
    {
        "code": "0452",
        "name": u"남문구"
    },
    {
        "code": "0131",
        "name": u"남문산"
    },
    {
        "code": "0317",
        "name": u"남성현"
    },
    {
        "code": "0048",
        "name": u"남원"
    },
    {
        "code": "0186",
        "name": u"남창"
    },
    {
        "code": "0152",
        "name": u"남춘천"
    },
    {
        "code": "0497",
        "name": u"남평"
    },
    {
        "code": "0361",
        "name": u"노안"
    },
    {
        "code": "0027",
        "name": u"논산"
    },
    {
        "code": "0391",
        "name": u"능곡"
    },
    {
        "code": "0132",
        "name": u"능주"
    },
    {
        "code": "0266",
        "name": u"다시"
    },
    {
        "code": "0176",
        "name": u"단성"
    },
    {
        "code": "0096",
        "name": u"단양"
    },
    {
        "code": "0247",
        "name": u"달천"
    },
    {
        "code": "0417",
        "name": u"대광리"
    },
    {
        "code": "0023",
        "name": u"대구"
    },
    {
        "code": "0148",
        "name": u"대성리"
    },
    {
        "code": "0310",
        "name": u"대신"
    },
    {
        "code": "0430",
        "name": u"대야"
    },
    {
        "code": "0010",
        "name": u"대전"
    },
    {
        "code": "0083",
        "name": u"대천"
    },
    {
        "code": "0233",
        "name": u"덕산"
    },
    {
        "code": "0168",
        "name": u"덕소"
    },
    {
        "code": "0052",
        "name": u"덕양"
    },
    {
        "code": "0209",
        "name": u"덕하"
    },
    {
        "code": "0111",
        "name": u"도계"
    },
    {
        "code": "0077",
        "name": u"도고온천"
    },
    {
        "code": "0095",
        "name": u"도담"
    },
    {
        "code": "0403",
        "name": u"도라산"
    },
    {
        "code": "0015",
        "name": u"동대구"
    },
    {
        "code": "0410",
        "name": u"동두천"
    },
    {
        "code": "0189",
        "name": u"동래"
    },
    {
        "code": "0450",
        "name": u"동백산"
    },
    {
        "code": "0366",
        "name": u"동산"
    },
    {
        "code": "0364",
        "name": u"동익산"
    },
    {
        "code": "0437",
        "name": u"동점"
    },
    {
        "code": "0113",
        "name": u"동해"
    },
    {
        "code": "0173",
        "name": u"동화"
    },
    {
        "code": "0615",
        "name": u"두정"
    },
    {
        "code": "0205",
        "name": u"득량"
    },
    {
        "code": "0059",
        "name": u"마산"
    },
    {
        "code": "0147",
        "name": u"마석"
    },
    {
        "code": "0038",
        "name": u"망상"
    },
    {
        "code": "0249",
        "name": u"매곡"
    },
    {
        "code": "0235",
        "name": u"명봉"
    },
    {
        "code": "0041",
        "name": u"목포"
    },
    {
        "code": "0074",
        "name": u"목행"
    },
    {
        "code": "0229",
        "name": u"몽탄"
    },
    {
        "code": "0236",
        "name": u"무안"
    },
    {
        "code": "0114",
        "name": u"묵호"
    },
    {
        "code": "0401",
        "name": u"문산"
    },
    {
        "code": "0224",
        "name": u"물금"
    },
    {
        "code": "0244",
        "name": u"미평"
    },
    {
        "code": "0120",
        "name": u"민둥산"
    },
    {
        "code": "0017",
        "name": u"밀양"
    },
    {
        "code": "0062",
        "name": u"반성"
    },
    {
        "code": "0738",
        "name": u"백마고지"
    },
    {
        "code": "0167",
        "name": u"백산"
    },
    {
        "code": "0258",
        "name": u"백양리"
    },
    {
        "code": "0034",
        "name": u"백양사"
    },
    {
        "code": "0089",
        "name": u"벌교"
    },
    {
        "code": "0451",
        "name": u"범일"
    },
    {
        "code": "0198",
        "name": u"별어곡"
    },
    {
        "code": "0069",
        "name": u"보성"
    },
    {
        "code": "0434",
        "name": u"봉성"
    },
    {
        "code": "0175",
        "name": u"봉양"
    },
    {
        "code": "0105",
        "name": u"봉화"
    },
    {
        "code": "0008",
        "name": u"부강"
    },
    {
        "code": "0020",
        "name": u"부산"
    },
    {
        "code": "0190",
        "name": u"부전"
    },
    {
        "code": "0464",
        "name": u"부조"
    },
    {
        "code": "0807",
        "name": u"부천"
    },
    {
        "code": "0222",
        "name": u"북영천"
    },
    {
        "code": "0064",
        "name": u"북천"
    },
    {
        "code": "0166",
        "name": u"분천"
    },
    {
        "code": "0185",
        "name": u"불국사"
    },
    {
        "code": "0312",
        "name": u"사곡"
    },
    {
        "code": "0255",
        "name": u"사릉"
    },
    {
        "code": "0193",
        "name": u"사방"
    },
    {
        "code": "0121",
        "name": u"사북"
    },
    {
        "code": "0143",
        "name": u"사상"
    },
    {
        "code": "0018",
        "name": u"삼랑진"
    },
    {
        "code": "0044",
        "name": u"삼례"
    },
    {
        "code": "0250",
        "name": u"삼산"
    },
    {
        "code": "0213",
        "name": u"삼탄"
    },
    {
        "code": "0080",
        "name": u"삽교"
    },
    {
        "code": "0272",
        "name": u"상동"
    },
    {
        "code": "0635",
        "name": u"상봉"
    },
    {
        "code": "0156",
        "name": u"상주"
    },
    {
        "code": "0257",
        "name": u"상천"
    },
    {
        "code": "0341",
        "name": u"서경주"
    },
    {
        "code": "0275",
        "name": u"서광주"
    },
    {
        "code": "0025",
        "name": u"서대전"
    },
    {
        "code": "0833",
        "name": u"서빙고"
    },
    {
        "code": "0001",
        "name": u"서울"
    },
    {
        "code": "0243",
        "name": u"서정리"
    },
    {
        "code": "0086",
        "name": u"서천"
    },
    {
        "code": "0325",
        "name": u"석불"
    },
    {
        "code": "0108",
        "name": u"석포"
    },
    {
        "code": "0199",
        "name": u"선평"
    },
    {
        "code": "0248",
        "name": u"성환"
    },
    {
        "code": "0411",
        "name": u"소요산"
    },
    {
        "code": "0142",
        "name": u"소정리"
    },
    {
        "code": "0188",
        "name": u"송정"
    },
    {
        "code": "0455",
        "name": u"수영"
    },
    {
        "code": "0003",
        "name": u"수원"
    },
    {
        "code": "0051",
        "name": u"순천"
    },
    {
        "code": "0161",
        "name": u"승부"
    },
    {
        "code": "0508",
        "name": u"신경주"
    },
    {
        "code": "0263",
        "name": u"신기"
    },
    {
        "code": "0182",
        "name": u"신녕"
    },
    {
        "code": "0223",
        "name": u"신동"
    },
    {
        "code": "0078",
        "name": u"신례원"
    },
    {
        "code": "0369",
        "name": u"신리"
    },
    {
        "code": "0174",
        "name": u"신림"
    },
    {
        "code": "0416",
        "name": u"신망리"
    },
    {
        "code": "0281",
        "name": u"신창"
    },
    {
        "code": "0465",
        "name": u"신창원"
    },
    {
        "code": "0265",
        "name": u"신탄리"
    },
    {
        "code": "0009",
        "name": u"신탄진"
    },
    {
        "code": "0032",
        "name": u"신태인"
    },
    {
        "code": "0245",
        "name": u"심천"
    },
    {
        "code": "0116",
        "name": u"쌍용"
    },
    {
        "code": "0503",
        "name": u"아산"
    },
    {
        "code": "0324",
        "name": u"아신"
    },
    {
        "code": "0202",
        "name": u"아우라지"
    },
    {
        "code": "0311",
        "name": u"아포"
    },
    {
        "code": "0192",
        "name": u"안강"
    },
    {
        "code": "0100",
        "name": u"안동"
    },
    {
        "code": "0135",
        "name": u"안양"
    },
    {
        "code": "0230",
        "name": u"약목"
    },
    {
        "code": "0171",
        "name": u"양동"
    },
    {
        "code": "0486",
        "name": u"양보"
    },
    {
        "code": "0269",
        "name": u"양수"
    },
    {
        "code": "0731",
        "name": u"양원"
    },
    {
        "code": "0463",
        "name": u"양자동"
    },
    {
        "code": "0091",
        "name": u"양평"
    },
    {
        "code": "0053",
        "name": u"여수 EXPO"
    },
    {
        "code": "0139",
        "name": u"여천"
    },
    {
        "code": "0195",
        "name": u"연당"
    },
    {
        "code": "0220",
        "name": u"연무대"
    },
    {
        "code": "0026",
        "name": u"연산"
    },
    {
        "code": "0415",
        "name": u"연천"
    },
    {
        "code": "0011",
        "name": u"영동"
    },
    {
        "code": "0002",
        "name": u"영등포"
    },
    {
        "code": "0117",
        "name": u"영월"
    },
    {
        "code": "0098",
        "name": u"영주"
    },
    {
        "code": "0103",
        "name": u"영천"
    },
    {
        "code": "0075",
        "name": u"예당"
    },
    {
        "code": "0119",
        "name": u"예미"
    },
    {
        "code": "0079",
        "name": u"예산"
    },
    {
        "code": "0162",
        "name": u"예천"
    },
    {
        "code": "0134",
        "name": u"오근장"
    },
    {
        "code": "0141",
        "name": u"오산"
    },
    {
        "code": "0297",
        "name": u"오송"
    },
    {
        "code": "0047",
        "name": u"오수"
    },
    {
        "code": "0067",
        "name": u"옥곡"
    },
    {
        "code": "0154",
        "name": u"옥산"
    },
    {
        "code": "0892",
        "name": u"옥수"
    },
    {
        "code": "0022",
        "name": u"옥천"
    },
    {
        "code": "0076",
        "name": u"온양온천"
    },
    {
        "code": "0484",
        "name": u"완사"
    },
    {
        "code": "0836",
        "name": u"왕십리"
    },
    {
        "code": "0014",
        "name": u"왜관"
    },
    {
        "code": "0618",
        "name": u"외고산"
    },
    {
        "code": "0159",
        "name": u"용궁"
    },
    {
        "code": "0347",
        "name": u"용동"
    },
    {
        "code": "0169",
        "name": u"용문"
    },
    {
        "code": "0104",
        "name": u"용산"
    },
    {
        "code": "0733",
        "name": u"운천"
    },
    {
        "code": "0509",
        "name": u"울산"
    },
    {
        "code": "0084",
        "name": u"웅천"
    },
    {
        "code": "0215",
        "name": u"원동"
    },
    {
        "code": "0479",
        "name": u"원북"
    },
    {
        "code": "0092",
        "name": u"원주"
    },
    {
        "code": "0217",
        "name": u"월내"
    },
    {
        "code": "0383",
        "name": u"율촌"
    },
    {
        "code": "0072",
        "name": u"음성"
    },
    {
        "code": "0101",
        "name": u"의성"
    },
    {
        "code": "0264",
        "name": u"의정부"
    },
    {
        "code": "0055",
        "name": u"이양"
    },
    {
        "code": "0300",
        "name": u"이원"
    },
    {
        "code": "0030",
        "name": u"익산"
    },
    {
        "code": "0921",
        "name": u"인천공항"
    },
    {
        "code": "0227",
        "name": u"일광"
    },
    {
        "code": "0040",
        "name": u"일로"
    },
    {
        "code": "0395",
        "name": u"일산"
    },
    {
        "code": "0204",
        "name": u"일신"
    },
    {
        "code": "0165",
        "name": u"임기"
    },
    {
        "code": "0362",
        "name": u"임성리"
    },
    {
        "code": "0046",
        "name": u"임실"
    },
    {
        "code": "0402",
        "name": u"임진강"
    },
    {
        "code": "0212",
        "name": u"입실"
    },
    {
        "code": "0197",
        "name": u"자미원"
    },
    {
        "code": "0446",
        "name": u"장락"
    },
    {
        "code": "0035",
        "name": u"장성"
    },
    {
        "code": "0504",
        "name": u"장항"
    },
    {
        "code": "0454",
        "name": u"재송"
    },
    {
        "code": "0414",
        "name": u"전곡"
    },
    {
        "code": "0006",
        "name": u"전의"
    },
    {
        "code": "0045",
        "name": u"전주"
    },
    {
        "code": "0158",
        "name": u"점촌"
    },
    {
        "code": "0262",
        "name": u"정동진"
    },
    {
        "code": "0200",
        "name": u"정선"
    },
    {
        "code": "0033",
        "name": u"정읍"
    },
    {
        "code": "0093",
        "name": u"제천"
    },
    {
        "code": "0267",
        "name": u"제천순환"
    },
    {
        "code": "0088",
        "name": u"조성"
    },
    {
        "code": "0007",
        "name": u"조치원"
    },
    {
        "code": "0126",
        "name": u"좌천"
    },
    {
        "code": "0138",
        "name": u"주덕"
    },
    {
        "code": "0815",
        "name": u"주안"
    },
    {
        "code": "0234",
        "name": u"중리"
    },
    {
        "code": "0071",
        "name": u"증평"
    },
    {
        "code": "0308",
        "name": u"지탄"
    },
    {
        "code": "0170",
        "name": u"지평"
    },
    {
        "code": "0511",
        "name": u"진례"
    },
    {
        "code": "0066",
        "name": u"진상"
    },
    {
        "code": "0480",
        "name": u"진성"
    },
    {
        "code": "0056",
        "name": u"진영"
    },
    {
        "code": "0063",
        "name": u"진주"
    },
    {
        "code": "0278",
        "name": u"진주수목원"
    },
    {
        "code": "0140",
        "name": u"진해"
    },
    {
        "code": "0057",
        "name": u"창원"
    },
    {
        "code": "0512",
        "name": u"창원중앙"
    },
    {
        "code": "0751",
        "name": u"천마산"
    },
    {
        "code": "0005",
        "name": u"천안"
    },
    {
        "code": "0502",
        "name": u"천안아산"
    },
    {
        "code": "0109",
        "name": u"철암"
    },
    {
        "code": "0016",
        "name": u"청도"
    },
    {
        "code": "0090",
        "name": u"청량리"
    },
    {
        "code": "0155",
        "name": u"청리"
    },
    {
        "code": "0253",
        "name": u"청소"
    },
    {
        "code": "0070",
        "name": u"청주"
    },
    {
        "code": "0276",
        "name": u"청주공항"
    },
    {
        "code": "0149",
        "name": u"청평"
    },
    {
        "code": "0412",
        "name": u"초성리"
    },
    {
        "code": "0449",
        "name": u"추전"
    },
    {
        "code": "0133",
        "name": u"추풍령"
    },
    {
        "code": "0106",
        "name": u"춘양"
    },
    {
        "code": "0153",
        "name": u"춘천"
    },
    {
        "code": "0073",
        "name": u"충주"
    },
    {
        "code": "0396",
        "name": u"탄현"
    },
    {
        "code": "0102",
        "name": u"탑리"
    },
    {
        "code": "0714",
        "name": u"태금"
    },
    {
        "code": "0123",
        "name": u"태백"
    },
    {
        "code": "0125",
        "name": u"태화강"
    },
    {
        "code": "0110",
        "name": u"통리"
    },
    {
        "code": "0146",
        "name": u"퇴계원"
    },
    {
        "code": "0400",
        "name": u"파주"
    },
    {
        "code": "0085",
        "name": u"판교"
    },
    {
        "code": "0256",
        "name": u"평내호평"
    },
    {
        "code": "0130",
        "name": u"평촌"
    },
    {
        "code": "0004",
        "name": u"평택"
    },
    {
        "code": "0058",
        "name": u"포항"
    },
    {
        "code": "0097",
        "name": u"풍기"
    },
    {
        "code": "0065",
        "name": u"하동"
    },
    {
        "code": "0238",
        "name": u"하양"
    },
    {
        "code": "0129",
        "name": u"한림정"
    },
    {
        "code": "0413",
        "name": u"한탄강"
    },
    {
        "code": "0196",
        "name": u"함백"
    },
    {
        "code": "0060",
        "name": u"함안"
    },
    {
        "code": "0029",
        "name": u"함열"
    },
    {
        "code": "0157",
        "name": u"함창"
    },
    {
        "code": "0039",
        "name": u"함평"
    },
    {
        "code": "0127",
        "name": u"해운대"
    },
    {
        "code": "0390",
        "name": u"행신"
    },
    {
        "code": "0107",
        "name": u"현동"
    },
    {
        "code": "0211",
        "name": u"호계"
    },
    {
        "code": "0081",
        "name": u"홍성"
    },
    {
        "code": "0210",
        "name": u"화명"
    },
    {
        "code": "0183",
        "name": u"화본"
    },
    {
        "code": "0054",
        "name": u"화순"
    },
    {
        "code": "0128",
        "name": u"황간"
    },
    {
        "code": "0136",
        "name": u"횡천"
    },
    {
        "code": "0458",
        "name": u"효문"
    },
    {
        "code": "0191",
        "name": u"효자"
    },
    {
        "code": "0274",
        "name": u"효천"
    },
    {
        "code": "0343",
        "name": u"흑석리"
    },
    {
        "code": "0178",
        "name": u"희방사"
    },
]

########NEW FILE########
__FILENAME__ = test
import unittest
from getpass import getpass
from korail import Korail, KorailError


class TestKorail(unittest.TestCase):

    korail = Korail()

    def test_0_login(self):
        user_id = raw_input("ID: ")
        password = getpass()
        phone_signing = raw_input("Use Phone Signing? (y/N) ").lower() == 'y'
        rv = self.korail.login(user_id, password, phone_signing)
        self.assertEqual(rv, True)

    def test_1_search_ktx(self):
        from datetime import datetime
        dep = '0001'
        arr = '0015'
        train_type = '00'
        date = datetime.strftime(datetime.now(), '%Y%m%d')
        time = datetime.strftime(datetime.now(), '%H%M%S')

        try:
            trains = self.korail.search_train(dep, arr, date, time, train_type)
        except KorailError as e:
            self.fail(e.message.encode('utf-8'))

        for train in trains:
            if train.train_type != '00' and train.train_type != '07':
                self.fail('Non-KTX train(%s) is included in search result.' %
                          train.train_type)

    def test_2_search_reserve(self):
        from datetime import datetime
        dep = '0001'
        arr = '0015'
        date = datetime.strftime(datetime.now(), '%Y%m%d')
        time = datetime.strftime(datetime.now(), '%H%M%S')

        try:
            trains = self.korail.search_train(dep, arr, date, time)
        except KorailError as e:
            self.fail(e.message.encode('utf-8'))

        tickets_count = len(self.korail.tickets())

        try:
            self.korail.reserve(trains[-1])
        except KorailError as e:
            self.fail(e.message.encode('utf-8'))

        tickets = self.korail.tickets()
        self.assertEqual(len(tickets), tickets_count + 1)

    def test_4_cancel_all(self):
        tickets = self.korail.tickets()
        for ticket in tickets:
            self.korail.cancel_ticket(ticket)
        tickets = self.korail.tickets()
        self.assertEqual(len(tickets), 0)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
