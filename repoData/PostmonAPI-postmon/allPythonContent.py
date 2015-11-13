__FILENAME__ = CepTracker
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

import requests
import re
import logging
import os

logger = logging.getLogger(__name__)


class CepTracker():

    def __init__(self):
        self.url = 'http://m.correios.com.br/movel/buscaCepConfirma.do'

    def _request(self, cep):
        response = requests.post(self.url, data={
            'cepEntrada': cep,
            'tipoCep': '',
            'cepTemp': '',
            'metodo': 'buscarCep'
        })
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            logger.exception('Erro no site dos Correios')
            raise ex
        return response.text

    def _get_infos_(self, cep):
        from lxml.html import fromstring
        response = self._request(cep)
        html = fromstring(response)
        registro_csspattern = '.caixacampobranco, .caixacampoazul'
        registros = html.cssselect(registro_csspattern)

        resultado = []
        for item in registros:
            item_csspattern = '.resposta, .respostadestaque'
            resultado.append([a.text for a in item.cssselect(item_csspattern)])

        return resultado

    def track(self, cep):
        itens = self._get_infos_(cep)
        result = []

        for item in itens:

            data = dict()
            data["v_date"] = datetime.now()

            for label, value in zip(item[0::2], item[1::2]):

                label = label.lower().strip(' :')
                value = re.sub('\s+', ' ', value.strip())

                if 'localidade' in label:
                    cidade, estado = value.split('/', 1)
                    data['cidade'] = cidade.strip()
                    data['estado'] = estado.split('-')[0].strip()
                elif 'logradouro' in label and ' - ' in value:
                    logradouro, complemento = value.split(' - ', 1)
                    data['logradouro'] = logradouro.strip()
                    data['complemento'] = complemento.strip(' -')
                else:
                    data[label] = value

            result.append(data)

        return result

########NEW FILE########
__FILENAME__ = database
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pymongo


class MongoDb(object):

    _fields = [
        'logradouro',
        'bairro',
        'cidade',
        'estado',
        'complemento'
    ]

    def __init__(self, address='localhost'):
        self._client = pymongo.MongoClient(address)
        USERNAME = os.environ.get('POSTMON_DB_USER')
        PASSWORD = os.environ.get('POSTMON_DB_PASSWORD')
        if all((USERNAME, PASSWORD)):
            self._client.postmon.authenticate(USERNAME, PASSWORD)
        self._db = self._client.postmon

    def get_one(self, cep, **kwargs):
        return self._db.ceps.find_one({'cep': cep}, **kwargs)

    def get_one_uf(self, sigla, **kwargs):
        return self._db.ufs.find_one({'sigla': sigla}, **kwargs)

    def get_one_cidade(self, sigla_uf_nome_cidade, **kwargs):
        spec = {'sigla_uf_nome_cidade': sigla_uf_nome_cidade}
        return self._db.cidades.find_one(spec, **kwargs)

    def get_one_uf_by_nome(self, nome, **kwargs):
        return self._db.ufs.find_one({'nome': nome}, **kwargs)

    def insert_or_update(self, obj, **kwargs):

        update = {'$set': obj}
        empty_fields = set(self._fields) - set(obj)
        update['$unset'] = dict((x, 1) for x in empty_fields)

        self._db.ceps.update({'cep': obj['cep']}, update, upsert=True)

    def insert_or_update_uf(self, obj, **kwargs):
        update = {'$set': obj}
        self._db.ufs.update({'sigla': obj['sigla']}, update, upsert=True)

    def insert_or_update_cidade(self, obj, **kwargs):
        update = {'$set': obj}
        chave = 'sigla_uf_nome_cidade'
        self._db.cidades.update({chave: obj[chave]}, update, upsert=True)

    def remove(self, cep):
        self._db.ceps.remove({'cep': cep})

########NEW FILE########
__FILENAME__ = IbgeTracker
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from lxml.html import fromstring
from database import MongoDb as Database


class IbgeTracker():

    def __init__(self):
        self.url_ufs = 'http://www.ibge.gov.br/home/geociencias' + \
                       '/areaterritorial/principal.shtm'
        self.url_cidades = 'http://www.ibge.gov.br/home/geociencias' + \
                           '/areaterritorial/area.php?nome=%'

    def _request(self, url):
        response = requests.post(url)
        response.raise_for_status()
        return response.text

    def _get_info_ufs(self, siglas):
        texto = self._request(self.url_ufs)
        html = fromstring(texto)
        seletorcss_linhas = "div#miolo_interno > table > tr"
        linhas = html.cssselect(seletorcss_linhas)
        linhas.pop()  # a primeira é o cabeçalho
        infos = []
        for linha in linhas:
            seletorcss_celulas = "td"
            celulas = linha.cssselect(seletorcss_celulas)
            codigo_ibge = celulas[0].text_content()
            if codigo_ibge in siglas:
                sigla = siglas[codigo_ibge]
                infos.append({
                    'sigla': sigla,
                    'codigo_ibge': codigo_ibge,
                    'nome': celulas[1].text_content(),
                    'area_km2': celulas[2].text_content()
                })

        #  neste ponto, após a carga
        #  das cidades, a lista
        #  'infos' deve estar populada

        return infos

    def _get_info_cidades(self):
        texto = self._request(self.url_cidades)
        html = fromstring(texto)
        seletorcss_linhas = "div#miolo_interno > table > tr"
        linhas = html.cssselect(seletorcss_linhas)
        linhas.pop()  # a primeira é o cabeçalho
        infos = []
        for linha in linhas:
            seletorcss_celulas = "td"
            celulas = linha.cssselect(seletorcss_celulas)
            infos.append({
                'codigo_ibge_uf': celulas[0].text_content(),
                'sigla_uf': celulas[1].text_content(),
                'codigo_ibge': celulas[2].text_content(),
                'nome': celulas[3].text_content(),
                'area_km2': celulas[4].text_content()
            })
        return infos

    def _track_ufs(self, db, siglas):
        infos = self._get_info_ufs(siglas)
        for info in infos:
            db.insert_or_update_uf(info)

    def _track_cidades(self, db):
        infos = self._get_info_cidades()
        siglas = {}
        for info in infos:
            codigo_ibge_uf = info['codigo_ibge_uf']
            sigla_uf = info['sigla_uf']
            nome = info['nome']
            if codigo_ibge_uf not in siglas:
                siglas[codigo_ibge_uf] = sigla_uf

            # a chave única de uma cidade não
            # pode ser só o nome, pois
            # existem cidades com mesmo nome
            # em estados diferentes
            info['sigla_uf_nome_cidade'] = '%s_%s' % (sigla_uf, nome)

            db.insert_or_update_cidade(info)

        return siglas

    def track(self, db):
        """
        Atualiza as bases internas do mongo
        com os dados mais recentes do IBGE
        referente a ufs e cidades
        """
        siglas = self._track_cidades(db)
        # siglas é um dict cod_ibge -> sigla:
        # { '35': 'SP', '35': 'RJ', ... }
        self._track_ufs(db, siglas)


def _standalone():
    db = Database()
    ibge = IbgeTracker()
    ibge.track(db)


if __name__ == "__main__":
    _standalone()

########NEW FILE########
__FILENAME__ = PostmonServer
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import bottle
import json
import logging
import xmltodict
from bottle import route, run, response, template, HTTPResponse
from CepTracker import CepTracker
import requests
from packtrack import Correios, Royal
from database import MongoDb as Database


logger = logging.getLogger(__name__)

app_v1 = bottle.Bottle()
jsonp_query_key = 'callback'


def expired(record_date):
    if 'v_date' not in record_date:
        True

    from datetime import datetime, timedelta

    # 6 months
    WEEKS = 26

    now = datetime.now()

    return (now - record_date['v_date'] >= timedelta(weeks=WEEKS))


def _get_info_from_source(cep):
    tracker = CepTracker()
    info = tracker.track(cep)
    if len(info) == 0:
        raise ValueError('CEP %s nao encontrado' % cep)
    return info


def format_result(result):
    # checa se foi solicitada resposta em JSONP
    js_func_name = bottle.request.query.get(jsonp_query_key)

    # checa se foi solicitado xml
    format = bottle.request.query.get('format')
    if format == 'xml':
        response.content_type = 'application/xml'
        return xmltodict.unparse({'result': result})

    if js_func_name:
        # se a resposta vai ser JSONP, o content type deve ser js e seu
        # conteudo deve ser JSON
        response.content_type = 'application/javascript'
        result = json.dumps(result)

        result = '%s(%s);' % (js_func_name, result)
    return result


def make_error(message):
    formats = {
        'json': 'application/json',
        'xml': 'application/xml',
        'jsonp': 'application/javascript',
    }
    format_ = bottle.request.query.get('format', 'json')
    return HTTPResponse(status=message, content_type=formats[format_])


def _get_estado_info(db, sigla):
    sigla = sigla.upper()
    return db.get_one_uf(sigla, fields={'_id': False, 'sigla': False})


def _get_cidade_info(db, sigla_uf, nome_cidade):
    sigla_uf = sigla_uf.upper()
    sigla_uf_nome_cidade = '%s_%s' % (sigla_uf, nome_cidade)
    fields = {
        '_id': False,
        'sigla_uf': False,
        'codigo_ibge_uf': False,
        'sigla_uf_nome_cidade': False,
        'nome': False
    }
    return db.get_one_cidade(sigla_uf_nome_cidade, fields=fields)


@route('/cep/<cep:re:\d{5}-?\d{3}>')
@app_v1.route('/cep/<cep:re:\d{5}-?\d{3}>')
def verifica_cep(cep):
    cep = cep.replace('-', '')
    db = Database()
    response.headers['Access-Control-Allow-Origin'] = '*'
    message = None

    result = db.get_one(cep, fields={'_id': False})
    if not result or expired(result):
        result = None
        try:
            info = _get_info_from_source(cep)
        except ValueError:
            message = '404 CEP %s nao encontrado' % cep
            logger.exception(message)
        except requests.exceptions.RequestException:
            message = '503 Servico Temporariamente Indisponivel'
            logger.exception(message)
        else:
            for item in info:
                db.insert_or_update(item)
            result = db.get_one(cep, fields={'_id': False, 'v_date': False})

        if not result:
            if not message:
                message = '404 CEP %s nao encontrado' % cep
                logger.warning(message)
            return make_error(message)

    result.pop('v_date', None)
    response.headers['Cache-Control'] = 'public, max-age=2592000'
    sigla_uf = result['estado']
    estado_info = _get_estado_info(db, sigla_uf)
    if estado_info:
        result['estado_info'] = estado_info
    nome_cidade = result['cidade']
    cidade_info = _get_cidade_info(db, sigla_uf, nome_cidade)
    if cidade_info:
        result['cidade_info'] = cidade_info
    return format_result(result)


@app_v1.route('/uf/<sigla>')
def uf(sigla):
    db = Database()
    result = _get_estado_info(db, sigla)
    if result:
        response.headers['Cache-Control'] = 'public, max-age=2592000'
        return format_result(result)
    else:
        message = '404 Estado %s nao encontrado' % sigla
        logger.warning(message)
        return make_error(message)


@app_v1.route('/cidade/<sigla_uf>/<nome>')
def cidade(sigla_uf, nome):
    db = Database()
    result = _get_cidade_info(db, sigla_uf, nome)
    if result:
        response.headers['Cache-Control'] = 'public, max-age=2592000'
        return format_result(result)
    else:
        message = '404 Cidade %s-%s nao encontrada' % (nome, sigla_uf)
        logger.warning(message)
        return make_error(message)


@app_v1.route('/rastreio/<provider>/<track>')
def track_pack(provider, track):
    if provider == 'ect':
        try:
            encomenda = Correios.encomenda(track)

            resposta = dict()
            result = []

            for status in encomenda.status:
                historico = dict()
                historico['data'] = status.data
                historico['local'] = status.local
                historico['situacao'] = status.situacao
                historico['detalhes'] = status.detalhes

                result.append(historico)

            resposta['servico'] = provider
            resposta['codigo'] = track
            resposta['historico'] = result

            return format_result(resposta)

        except AttributeError:
            message = "404 Pacote %s nao encontrado" % track
            logger.exception(message)
    else:
        message = '404 Servico %s nao encontrado' % provider
        logger.warning(message)
    return make_error(message)

bottle.mount('/v1', app_v1)


@route('/crossdomain.xml')
def crossdomain():
    response.content_type = 'application/xml'
    return template('crossdomain')


def _standalone(port=9876):
    run(host='0.0.0.0', port=port)


if __name__ == "__main__":
    _standalone()

########NEW FILE########
__FILENAME__ = PostmonTaskScheduler
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import timedelta
from celery import Celery
from celery.utils.log import get_task_logger
from IbgeTracker import IbgeTracker
from database import MongoDb as Database
import os

USERNAME = os.environ.get('POSTMON_DB_USER')
PASSWORD = os.environ.get('POSTMON_DB_PASSWORD')
if all((USERNAME, PASSWORD)):
    broker_conn_string = 'mongodb://%s:%s@localhost:27017' \
        % (USERNAME, PASSWORD)
else:
    broker_conn_string = 'mongodb://localhost:27017'

print(broker_conn_string)

app = Celery('postmon', broker=broker_conn_string)

app.conf.update(
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
    CELERY_RESULT_SERIALIZER='json',
    CELERY_TIMEZONE='America/Sao_Paulo',
    CELERY_ENABLE_UTC=True,
    CELERYBEAT_SCHEDULE={
        'track_ibge_daily': {
            'task': 'PostmonTaskScheduler.track_ibge',
            'schedule': timedelta(days=1)  # útil para
                                           # testes: timedelta(minutes=1)
        }
    }
)

logger = get_task_logger(__name__)


@app.task
def track_ibge():
    logger.info('Iniciando tracking do IBGE...')
    db = Database()
    ibge = IbgeTracker()
    ibge.track(db)
    logger.info('Finalizou o tracking do IBGE')

########NEW FILE########
__FILENAME__ = database_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest

from database import MongoDb


class MongoDbTest(unittest.TestCase):

    def setUp(self):
        self.db = MongoDb()

        self.db.insert_or_update({
            'cep': 'UNIQUE_KEY',
            'logradouro': 'A',
            'bairro': 'A',
            'cidade': 'A',
            'estado': 'A'
        })

    def test_remove_empty_fields(self):

        '''
        Quando um registro é atualizado no banco de dados,
        as chaves inexistentes devem ser removidas.
        '''

        self.db.insert_or_update({
            'cep': 'UNIQUE_KEY',
            'estado': 'B'
        })

        result = self.db.get_one('UNIQUE_KEY')

        self.assertEqual(result['estado'], 'B')
        self.assertNotIn('logradouro', result)
        self.assertNotIn('bairro', result)
        self.assertNotIn('cidade', result)

    def tearDown(self):
        self.db.remove('UNIQUE_KEY')

########NEW FILE########
__FILENAME__ = postmon_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import re
import unittest
import mock

import webtest
import bottle
from requests import RequestException

import CepTracker
import PostmonServer

bottle.DEBUG = True


class PostmonBaseTest(object):

    expected = {
        '01330000': [{
            'logradouro': 'Rua Rocha',
            'bairro': 'Bela Vista',
            'cidade': u'São Paulo',
            'estado': 'SP'
        }],
        '85100000': [{
            'cidade': u'Jordão (Guarapuava)',
            'estado': 'PR'
        }],
        '75064590': [{
            'logradouro': 'Rua A',
            'bairro': 'Vila Jaiara',
            'cidade': u'Anápolis',
            'estado': 'GO'
        }, {
            'logradouro': 'Rua A',
            'bairro': 'Vila Jaiara Setor Leste',
            'cidade': u'Anápolis',
            'estado': 'GO'
        }],
        '12245230': [{
            'logradouro': u'Avenida Tivoli',
            'complemento': u'lado ímpar',
            'bairro': u'Vila Betânia',
            'cidade': u'São José dos Campos',
            'estado': 'SP'
        }],
        '69908768': [{
            'logradouro': 'Rodovia BR-364 (Rio Branco-Porto Velho)',
            'complemento': u'até 5014 - lado par',
            'bairro': 'Loteamento Santa Helena',
            'cidade': 'Rio Branco',
            'estado': 'AC'
        }]
    }

    def test_cep_com_rua(self):
        self.assertCep('01330000')

    def test_cep_sem_rua(self):
        self.assertCep('85100000')

    def test_cep_inexistente(self):
        self.assertCep('99999999')

    def test_cep_com_mais_de_um_resultado(self):
        self.assertCep('75064590')

    def test_ceps_com_complemento(self):
        self.assertCep('12245230')
        self.assertCep('69908768')


class CepTrackerTest(unittest.TestCase, PostmonBaseTest):

    def setUp(self):
        self.tracker = CepTracker.CepTracker()

    def get_cep(self, cep):
        return self.tracker.track(cep)

    def assertCep(self, cep):

        result = self.get_cep(cep)
        expected = self.expected.get(cep, [])

        self.assertEqual(len(expected), len(result))

        for e, r in zip(expected, result):
            for key, value in e.items():
                self.assertIn(key, r)
                self.assertEqual(value, r[key])

            self.assertIn('v_date', r)


class CepTrackerMockTest(CepTrackerTest):

    '''
    O CepTrackerMockTest usa arquivos locais com os resultados
    obtidos nos Correios. Assim é possível saber se os testes do
    CepTrackerTest quebraram por problemas no código ou por alteração
    nos Correios.
    '''

    def setUp(self):
        self.tracker = CepTracker.CepTracker()
        self.tracker._request = self._request_mock

    def _request_mock(self, cep):
        with open('test/assets/' + cep + '.html') as f:
            return f.read().decode('latin-1')


class PostmonWebTest(unittest.TestCase, PostmonBaseTest):

    '''
    Teste do servidor do Postmon
    '''

    def setUp(self):
        self.app = webtest.TestApp(bottle.app())

    def get_cep(self, cep):
        response = self.app.get('/cep/' + cep)
        return response.json

    def assertCep(self, cep):
        expected = self.expected.get(cep, None)
        try:
            result = self.get_cep(cep)
        except webtest.AppError as ex:
            if not expected and '404' in ex.message and cep in ex.message:
                return
            raise ex

        for k, v in expected[0].items():
            self.assertEqual(v, result[k])

        self.assertNotIn('v_date', result)


class PostmonWebJSONPTest(PostmonWebTest):
    '''
    Teste de requisições JSONP no servidor do Postmon
    '''

    def setUp(self):
        self.jsonp_query_key = PostmonServer.jsonp_query_key
        self.jsonp_func_name = 'func_name'
        super(PostmonWebJSONPTest, self).setUp()

    def get_cep(self, cep):
        response = self.app.get(
            '/cep/%s?%s=%s' % (cep,
                               self.jsonp_query_key,
                               self.jsonp_func_name))

        regexp = re.compile('^%s\((.*)\);$' % self.jsonp_func_name)
        json_data = re.findall(regexp, response.body)[0]

        return json.loads(json_data)


class PostmonV1WebTest(PostmonWebTest):

    '''
    Teste do servidor do Postmon no /v1
    '''

    def get_cep(self, cep):
        response = self.app.get('/v1/cep/' + cep)
        return response.json


class PostmonXMLTest(unittest.TestCase):
    """ testa requisições XML """

    def setUp(self):
        self.app = webtest.TestApp(bottle.app())

    def get_cep(self, cep):
        response = self.app.get(
            '/cep/%s?format=xml' % cep
        )
        return response

    def test_xml_return(self):
        import xmltodict
        response = self.get_cep('06708070')
        parsed = xmltodict.parse(response.body)
        result = parsed.get('result')
        self.assertEqual(result['bairro'], u'Parque S\xe3o George')
        self.assertEqual(result['cidade'], u'Cotia')
        self.assertEqual(result['cep'], u'06708070')
        self.assertEqual(result['estado'], u'SP')
        self.assertEqual(result['logradouro'], u'Avenida Eid Mansur')


class PostmonErrors(unittest.TestCase):

    def setUp(self):
        self.app = webtest.TestApp(bottle.app())

    def get_cep(self, cep, format='json', expect_errors=False):
        endpoint = '/cep/%s' % cep
        if format == 'xml':
            endpoint += '?format=xml'
        response = self.app.get(endpoint, expect_errors=expect_errors)
        return response

    @mock.patch('PostmonServer._get_info_from_source')
    def test_404_status(self, _mock):
        _mock.side_effect = ValueError('test')
        response = self.get_cep('99999999', expect_errors=True)
        self.assertEqual("404 CEP 99999999 nao encontrado", response.status)
        self.assertEqual('application/json', response.headers['Content-Type'])
        self.assertEqual('', response.body)

    @mock.patch('PostmonServer._get_info_from_source')
    def test_404_status_with_xml_format(self, _mock):
        _mock.side_effect = ValueError('test')
        response = self.get_cep('99999999', format='xml', expect_errors=True)
        self.assertEqual("404 CEP 99999999 nao encontrado", response.status)
        self.assertEqual('application/xml', response.headers['Content-Type'])
        self.assertEqual('', response.body)

    @mock.patch('PostmonServer._get_info_from_source')
    def test_503_status(self, _mock):
        _mock.side_effect = RequestException
        response = self.get_cep('99999999', expect_errors=True)
        self.assertEqual("503 Servico Temporariamente Indisponivel",
                         response.status)
        self.assertEqual('application/json', response.headers['Content-Type'])
        self.assertEqual('', response.body)

    @mock.patch('PostmonServer._get_info_from_source')
    def test_503_status_with_xml_format(self, _mock):
        _mock.side_effect = RequestException
        response = self.get_cep('99999999', format='xml', expect_errors=True)
        self.assertEqual("503 Servico Temporariamente Indisponivel",
                         response.status)
        self.assertEqual('application/xml', response.headers['Content-Type'])
        self.assertEqual('', response.body)

########NEW FILE########
