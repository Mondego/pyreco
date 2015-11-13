__FILENAME__ = base
# -*- coding: utf-8 -*-

class Entidade(object):
    _fonte_dados = None

    def __init__(self, **kwargs):
        # Codigo para dinamizar a criacao de instancias de entidade,
        # aplicando os valores dos atributos na instanciacao
        for k, v in kwargs.items():
            setattr(self, k, v)

        # Adiciona o objeto à fonte de dados informada
        if not self._fonte_dados:
            from fonte_dados import _fonte_dados
            self._fonte_dados = _fonte_dados

        self._fonte_dados.adicionar_objeto(self)

    def __repr__(self):
        return '<%s %s>'%(self.__class__.__name__, str(self))

class Lote(object):
    pass


########NEW FILE########
__FILENAME__ = certificado
# -*- coding: utf-8 -*-
import os

from base import Entidade

from OpenSSL import crypto

class Certificado(Entidade):
    u"""Classe abstrata responsavel por definir o modelo padrao para as demais
    classes de certificados digitais.
    
    Caso va implementar um novo formato de certificado, crie uma classe que
    herde desta."""

    def __new__(cls, *args, **kwargs):
        if cls == Certificado:
            raise Exception('Esta classe nao pode ser instanciada diretamente!')
        else:
            return super(Certificado, cls).__new__(cls, *args, **kwargs)

class CertificadoA1(Certificado):
    u"""Implementa a entidade do certificado eCNPJ A1, suportado pelo OpenSSL,
    e amplamente utilizado."""

    caminho_arquivo = None
    conteudo_x509 = None
    pasta_temporaria = '/tmp/'
    arquivo_chave = 'key.pem'
    arquivo_cert = 'cert.pem'

    def __init__(self, caminho_arquivo=None, conteudo_x509=None):
        self.caminho_arquivo = caminho_arquivo or self.caminho_arquivo
        self.conteudo_x509 = conteudo_x509 or self.conteudo_x509
    
    def separar_arquivo(self, senha, caminho_chave=None, caminho_cert=None):
        u"""Separa o arquivo de certificado em dois: de chave e de certificado,
        em arquivos temporários separados"""
        
        caminho_chave = caminho_chave or os.path.join(self.pasta_temporaria, self.arquivo_chave)
        caminho_cert = caminho_cert or os.path.join(self.pasta_temporaria, self.arquivo_cert)

        # Lendo o arquivo pfx no formato pkcs12 como binario
        pkcs12 = crypto.load_pkcs12(file(self.caminho_arquivo, 'rb').read(), senha)

        # Retorna a string decodificado da chave privada
        key_str = crypto.dump_privatekey(crypto.FILETYPE_PEM, pkcs12.get_privatekey())

        # Retorna a string decodificado do certificado
        cert_str = crypto.dump_certificate(crypto.FILETYPE_PEM, pkcs12.get_certificate())

        # Gravando a string no dicso
        file(caminho_cert, 'wb').write(cert_str)

        # Gravando a string no dicso
        file(caminho_chave, 'wb').write(key_str)

        return caminho_chave, caminho_cert


########NEW FILE########
__FILENAME__ = cliente
# -*- coding: utf-8 -*-
from base import Entidade
from pynfe.utils.flags import TIPOS_DOCUMENTO, CODIGO_BRASIL

class Cliente(Entidade):
    # Dados do Cliente
    # - Nome/Razão Social (obrigatorio)
    razao_social = str()

    # - Tipo de Documento (obrigatorio) - default CNPJ - TIPOS_DOCUMENTO
    tipo_documento = 'CNPJ'

    # - Numero do Documento (obrigatorio)
    numero_documento = str()

    # - Inscricao Estadual
    inscricao_estadual = str()

    # - Inscricao SUFRAMA
    inscricao_suframa = str()

    # - Isento do ICMS (Sim/Nao)
    isento_icms = False

    # Endereco
    # - Logradouro (obrigatorio)
    endereco_logradouro = str()

    # - Numero (obrigatorio)
    endereco_numero = str()

    # - Complemento
    endereco_complemento = str()

    # - Bairro (obrigatorio)
    endereco_bairro = str()

    # - CEP
    endereco_cep = str()

    # - Pais (seleciona de lista)
    endereco_pais = CODIGO_BRASIL

    # - UF (obrigatorio)
    endereco_uf = str()

    # - Municipio (obrigatorio)
    endereco_municipio = str()

    # - Telefone
    endereco_telefone = str()

    def __str__(self):
        return ' '.join([self.tipo_documento, self.numero_documento])


########NEW FILE########
__FILENAME__ = emitente
from base import Entidade
from pynfe.utils.flags import CODIGO_BRASIL

class Emitente(Entidade):
    # Dados do Emitente
    # - Nome/Razao Social (obrigatorio)
    razao_social = str()

    # - Nome Fantasia
    nome_fantasia = str()

    # - CNPJ (obrigatorio)
    cnpj = str()

    # - Inscricao Estadual (obrigatorio)
    inscricao_estadual = str()

    # - CNAE Fiscal
    cnae_fiscal = str()

    # - Inscricao Municipal
    inscricao_municipal = str()

    # - Inscricao Estadual (Subst. Tributario)
    inscricao_estadual_subst_tributaria = str()

    # Endereco
    # - Logradouro (obrigatorio)
    endereco_logradouro = str()

    # - Numero (obrigatorio)
    endereco_numero = str()

    # - Complemento
    endereco_complemento = str()

    # - Bairro (obrigatorio)
    endereco_bairro = str()

    # - CEP
    endereco_cep = str()

    # - Pais (aceita somente Brasil)
    endereco_pais = CODIGO_BRASIL

    # - UF (obrigatorio)
    endereco_uf = str()

    # - Municipio (obrigatorio)
    endereco_municipio = str()

    # - Telefone
    endereco_telefone = str()

    # Logotipo
    logotipo = None

    def __str__(self):
        return self.cnpj


########NEW FILE########
__FILENAME__ = fonte_dados
# -*- coding: utf-8 -*-
from pynfe.excecoes import NenhumObjetoEncontrado, MuitosObjetosEncontrados

class FonteDados(object):
    u"""Classe responsável por ser o repositório dos objetos em memória e que
    pode ser extendida para persistir esses objetos. Também tem a função de
    memorizar os objetos redundantes como um só e assim otimizar o desempenho."""

    _objetos = None

    def __init__(self, objetos=None):
        # Inicializa variável que armazena os objetos contidos na Fonte de Dados
        if objetos:
            self._objetos = objetos
        else:
            self._objetos = []
    
    def carregar_objetos(self, **kwargs):
        u"""Método responsavel por retornar os objetos que casem com os atributos
        informados no argumento **kwargs (argumentos nomeados).
        
        Um argumento especial é o '_classe', que representa a classe da entidade
        desejada.

        FIXME: Este algoritimo pode ser melhorado pra fazer pesquisas melhores,
        mas por enquanto vamos nos focar no processo em geral para só depois nos
        preocupar com otimizações e desempenho."""

        # Função de filtro
        def filtrar(obj):
            ret = True

            for k,v in kwargs.items():
                # Filtra pela classe e pelos atributos
                ret = (k == '_classe' and isinstance(obj, v)) or\
                      (k != '_classe' and getattr(obj, k, None) == v)

                if not ret:
                    break

            return ret

        # Filtra a lista de objetos
        lista = filter(filtrar, self._objetos)

        return lista

    def adicionar_objeto(self, _objeto):
        u"""Método responsável por adicionar o(s) objeto(s) informado(s) ao
        repositorio de objetos da fonte de dados."""

        from base import Entidade

        # Adiciona _objeto como objeto
        if isinstance(_objeto, Entidade):
            self._objetos.append(_objeto)

        # Adiciona _objeto como lista
        elif isinstance(_objeto, (list, tuple)):
            self._objetos += _objeto

        else:
            raise Exception('Objeto informado e invalido!')

    def remover_objeto(self, _objeto=None, **kwargs):
        u"""Método responsavel por remover os objetos que casem com os atributos
        informados no argumento **kwargs (argumentos nomeados).
        
        Um argumento especial é o '_classe', que representa a classe da entidade
        desejada.
        
        Outro argumetno especial é o '_objeto', que representa o objeto a ser
        removido. Caso o argumento _objeto seja uma lista de objetos, eles serão
        removidos também."""

        from base import Entidade

        lista = None

        # Remove objetos
        if not _objeto:
            lista = self.carregar_objetos(**kwargs)

        # Remove _objeto como objeto
        elif isinstance(_objeto, Entidade):
            lista = [_objeto]

        # Remove _objeto como objeto
        elif isinstance(_objeto, (list, tuple)):
            lista = _objeto

        else:
            raise Exception('Objeto informado e invalido!')

        # Efetiva a remoção
        for obj in lista:
            self._objetos.remove(obj)

    def obter_objeto(self, **kwargs):
        u"""Faz a ponte para o método 'carregar_objetos' mas obriga o retorno de
        apenas um objeto, levantando exceção se nenhum for encontrado ou se forem
        encontrados mais de um."""
        
        lista = self.carregar_objetos(**kwargs)
        
        if len(lista) == 0:
            raise NenhumObjetoEncontrado('Nenhum objeto foi encontrado!')
        elif len(lista) > 1:
            raise MuitosObjetosEncontrados('Muitos objetos foram encontrados!')

        return lista[0]
    
    def obter_lista(self, **kwargs):
        u"""Método de proxy, que somente repassa a chamada ao metodo 'carregar_objetos'"""
        return self.carregar_objetos(**kwargs)
    
    def contar_objetos(self, **kwargs):
        u"""Método que repassa a chamada ao metodo 'carregar_objetos' mas retorna
        somente a quantidade de objetos encontrados."""

        if kwargs:
            return len(self.carregar_objetos(**kwargs))
        else:
            return len(self._objetos)

# Instancia da fonte de dados default
_fonte_dados = FonteDados()


########NEW FILE########
__FILENAME__ = lotes
from base import Lote

class LoteNotaFiscal(Lote):
    pass


########NEW FILE########
__FILENAME__ = notafiscal
# -*- coding: utf-8 -*-
import random

from base import Entidade
from pynfe import get_version
from pynfe.utils.flags import NF_STATUS, NF_TIPOS_DOCUMENTO, NF_TIPOS_IMPRESSAO_DANFE,\
        NF_FORMAS_PAGAMENTO, NF_FORMAS_EMISSAO, NF_FINALIDADES_EMISSAO,\
        NF_REFERENCIADA_TIPOS, NF_PRODUTOS_ESPECIFICOS, ICMS_TIPOS_TRIBUTACAO,\
        ICMS_ORIGENS, ICMS_MODALIDADES, IPI_TIPOS_TRIBUTACAO, IPI_TIPOS_CALCULO,\
        PIS_TIPOS_TRIBUTACAO, PIS_TIPOS_CALCULO, COFINS_TIPOS_TRIBUTACAO,\
        COFINS_TIPOS_CALCULO, MODALIDADES_FRETE, ORIGENS_PROCESSO, CODIGO_BRASIL,\
        NF_PROCESSOS_EMISSAO, CODIGOS_ESTADOS, TIPOS_DOCUMENTO
from pynfe.utils import so_numeros, memoize

from decimal import Decimal

class NotaFiscal(Entidade):
    status = NF_STATUS[0]

    # Código numérico aleatório que compõe a chave de acesso
    codigo_numerico_aleatorio = str()

    # Digito verificador do codigo numerico aleatorio
    dv_codigo_numerico_aleatorio = str()

    # Nota Fisca eletronica
    # - Modelo (formato: NN)
    modelo = int()

    # - Serie (obrigatorio - formato: NNN)
    serie = str()

    # - Numero NF (obrigatorio)
    numero_nf = str()

    # - Data da Emissao (obrigatorio)
    data_emissao = None

    # - Natureza da Operacao (obrigatorio)
    natureza_operacao = str()

    # - Tipo do Documento (obrigatorio - seleciona de lista) - NF_TIPOS_DOCUMENTO
    tipo_documento = int()

    # - Processo de emissão da NF-e (obrigatorio - seleciona de lista) - NF_PROCESSOS_EMISSAO
    processo_emissao = 0

    # - Versao do processo de emissão da NF-e
    versao_processo_emissao = get_version()

    # - Tipo impressao DANFE (obrigatorio - seleciona de lista) - NF_TIPOS_IMPRESSAO_DANFE
    tipo_impressao_danfe = int()

    # - Data de saida/entrada
    data_saida_entrada = None

    # - Forma de pagamento  (obrigatorio - seleciona de lista) - NF_FORMAS_PAGAMENTO
    forma_pagamento = int()

    # - Forma de emissao (obrigatorio - seleciona de lista) - NF_FORMAS_EMISSAO
    forma_emissao = str()

    # - Finalidade de emissao (obrigatorio - seleciona de lista) - NF_FINALIDADES_EMISSAO
    finalidade_emissao = int()

    # - UF - converter para codigos em CODIGOS_ESTADOS
    uf = str()

    # - Municipio de ocorrencia
    municipio = str()

    # - Digest value da NF-e (somente leitura)
    digest_value = None

    # - Valor total da nota (somente leitura)
    valor_total_nota = Decimal()

    # - Valor ICMS da nota (somente leitura)
    valor_icms_nota = Decimal()

    # - Valor ICMS ST da nota (somente leitura)
    valor_icms_st_nota = Decimal()

    # - Protocolo (somente leitura)
    protocolo = str()

    # - Data (somente leitura)
    data = None

    # - Notas Fiscais Referenciadas (lista 1 para * / ManyToManyField)
    notas_fiscais_referenciadas = None

    # - Emitente (CNPJ ???)
    emitente = None

    # - Destinatario/Remetente
    #  - Identificacao (seleciona de Clientes)
    destinatario_remetente = None

    # - Entrega (XXX sera possivel ter entrega e retirada ao mesmo tempo na NF?)
    entrega = None

    # - Retirada
    retirada = None

    # - Local Retirada/Entrega
    #  - Local de retirada diferente do emitente (Sim/Nao)
    local_retirada_diferente_emitente = False

    #  - Local de entrega diferente do destinatario (Sim/Nao)
    local_entrega_diferente_destinatario = False

    # - Produtos e Servicos (lista 1 para * / ManyToManyField)
    produtos_e_servicos = None

    # Totais
    # - ICMS
    #  - Base de calculo (somente leitura)
    totais_icms_base_calculo = Decimal()

    #  - Total do ICMS (somente leitura)
    totais_icms_total = Decimal()

    #  - Base de calculo do ICMS ST (somente leitura)
    totais_icms_st_base_calculo = Decimal()

    #  - Total do ICMS ST (somente leitura)
    totais_icms_st_total = Decimal()

    #  - Total dos produtos e servicos (somente leitura)
    totais_icms_total_produtos_e_servicos = Decimal()

    #  - Total do frete (somente leitura)
    totais_icms_total_frete = Decimal()

    #  - Total do seguro (somente leitura)
    totais_icms_total_seguro = Decimal()

    #  - Total do desconto (somente leitura)
    totais_icms_total_desconto = Decimal()

    #  - Total do II (somente leitura)
    totais_icms_total_ii = Decimal()

    #  - Total do IPI (somente leitura)
    totais_icms_total_ipi = Decimal()

    #  - PIS (somente leitura)
    totais_icms_pis = Decimal()

    #  - COFINS (somente leitura)
    totais_icms_cofins = Decimal()

    #  - Outras despesas acessorias
    totais_icms_outras_despesas_acessorias = Decimal()

    #  - Total da nota
    totais_icms_total_nota = Decimal()

    # - ISSQN
    #  - Base de calculo do ISS
    totais_issqn_base_calculo_iss = Decimal()

    #  - Total do ISS
    totais_issqn_total_iss = Decimal()

    #  - PIS sobre servicos
    totais_issqn_pis = Decimal()

    #  - COFINS sobre servicos
    totais_issqn_cofins = Decimal()

    #  - Total dos servicos sob nao-incidencia ou nao tributados pelo ICMS
    totais_issqn_total = Decimal()

    # - Retencao de Tributos
    #  - Valor retido de PIS
    totais_retencao_valor_retido_pis = Decimal()

    #  - Valor retido de COFINS
    totais_retencao_valor_retido_cofins = Decimal()

    #  - Valor retido de CSLL
    totais_retencao_valor_retido_csll = Decimal()

    #  - Base de calculo do IRRF
    totais_retencao_base_calculo_irrf = Decimal()

    #  - Valor retido do IRRF
    totais_retencao_valor_retido_irrf = Decimal()

    #  - BC da ret. da Prev. Social
    totais_retencao_bc_retencao_previdencia_social = Decimal()

    #  - Retencao da Prev. Social
    totais_retencao_retencao_previdencia_social = Decimal()

    # Transporte
    # - Modalidade do Frete (obrigatorio - seleciona de lista) - MODALIDADES_FRETE
    #  - 0 - Por conta do emitente
    #  - 1 - Por conta do destinatario
    transporte_modalidade_frete = int()

    # - Transportador (seleciona de Transportadoras)
    transporte_transportadora = None

    # - Retencao do ICMS
    #  - Base de calculo
    transporte_retencao_icms_base_calculo = Decimal()

    #  - Aliquota
    transporte_retencao_icms_aliquota = Decimal()

    #  - Valor do servico
    transporte_retencao_icms_valor_servico = Decimal()

    #  - UF
    transporte_retencao_icms_uf = str()

    #  - Municipio
    transporte_retencao_icms_municipio = Decimal()

    #  - CFOP
    transporte_retencao_icms_cfop = str()

    #  - ICMS retido
    transporte_retencao_icms_retido = Decimal()

    # - Veiculo
    #  - Placa
    transporte_veiculo_placa = str()

    #  - RNTC
    transporte_veiculo_rntc = str()

    #  - UF
    transporte_veiculo_uf = str()

    # - Reboque
    #  - Placa
    transporte_reboque_placa = str()

    #  - RNTC
    transporte_reboque_rntc = str()

    #  - UF
    transporte_reboque_uf = str()

    # - Volumes (lista 1 para * / ManyToManyField)
    transporte_volumes = None

    # Cobranca
    # - Fatura
    #  - Numero
    fatura_numero = str()

    #  - Valor original
    fatura_valor_original = Decimal()

    #  - Valor do desconto
    fatura_valor_desconto = Decimal()

    #  - Valor liquido
    fatura_valor_liquido = Decimal()

    # - Duplicatas (lista 1 para * / ManyToManyField)
    duplicatas = None

    # Informacoes Adicionais
    # - Informacoes Adicionais
    #  - Informacoes adicionais de interesse do fisco
    informacoes_adicionais_interesse_fisco = str()

    #  - Informacoes complementares de interesse do contribuinte
    informacoes_complementares_interesse_contribuinte = str()

    # - Observacoes do Contribuinte (lista 1 para * / ManyToManyField)
    observacoes_contribuinte = None

    # - Processo Referenciado (lista 1 para * / ManyToManyField)
    processos_referenciados = None

    def __init__(self, *args, **kwargs):
        self.notas_fiscais_referenciadas = []
        self.produtos_e_servicos = []
        self.transporte_volumes = []
        self.duplicatas = []
        self.observacoes_contribuinte = []
        self.processos_referenciados = []

        super(NotaFiscal, self).__init__(*args, **kwargs)

    def __str__(self):
        return ' '.join([str(self.modelo), self.serie, self.numero_nf])

    def adicionar_nota_fiscal_referenciada(self, **kwargs):
        u"""Adiciona uma instancia de Nota Fisca referenciada"""
        obj = NotaFiscalReferenciada(**kwargs)
        self.notas_fiscais_referenciadas.append(obj)
        return obj

    def adicionar_produto_servico(self, **kwargs):
        u"""Adiciona uma instancia de Produto"""
        obj = NotaFiscalProduto(**kwargs)
        self.produtos_e_servicos.append(obj)
        return obj

    def adicionar_transporte_volume(self, **kwargs):
        u"""Adiciona uma instancia de Volume de Transporte"""
        obj = NotaFiscalTransporteVolume(**kwargs)
        self.transporte_volumes.append(obj)
        return obj

    def adicionar_duplicata(self, **kwargs):
        u"""Adiciona uma instancia de Duplicata"""
        obj = NotaFiscalCobrancaDuplicata(**kwargs)
        self.duplicatas.append(obj)
        return obj

    def adicionar_observacao_contribuinte(self, **kwargs):
        u"""Adiciona uma instancia de Observacao do Contribuinte"""
        obj = NotaFiscalObservacaoContribuinte(**kwargs)
        self.observacoes_contribuinte.append(obj)
        return obj

    def adicionar_processo_referenciado(self, **kwargs):
        u"""Adiciona uma instancia de Processo Referenciado"""
        obj = NotaFiscalProcessoReferenciado(**kwargs)
        self.processos_referenciados.append(obj)
        return obj

    @property
    @memoize
    def identificador_unico(self):
        # Monta 'Id' da tag raiz <infNFe>
        # Ex.: NFe35080599999090910270550010000000011518005123
        return "NFe%(uf)s%(ano)s%(mes)s%(cnpj)s%(mod)s%(serie)s%(nNF)s%(tpEmis)s%(cNF)s%(cDV)s"%{
                'uf': CODIGOS_ESTADOS[self.uf],
                'ano': self.data_emissao.strftime('%y'),
                'mes': self.data_emissao.strftime('%m'),
                'cnpj': so_numeros(self.emitente.cnpj),
                'mod': self.modelo,
                'serie': str(self.serie).zfill(3),
                'nNF': str(self.numero_nf).zfill(9),
                'tpEmis': str(self.forma_emissao),
                'cNF': self.codigo_numerico_aleatorio.zfill(8),
                'cDV': self.dv_codigo_numerico_aleatorio,
                }

class NotaFiscalReferenciada(Entidade):
    # - Tipo (seleciona de lista) - NF_REFERENCIADA_TIPOS
    tipo = str()

    #  - Nota Fiscal eletronica
    #   - Chave de Acesso
    chave_acesso = str()

    #  - Nota Fiscal
    #   - UF
    uf = str()

    #   - Mes e ano de emissao
    mes_ano_emissao = str()

    #   - CNPJ
    cnpj = str()

    #   - Serie (XXX)
    serie = str()

    #   - Numero
    numero = str()

    #   - Modelo
    modelo = str()


class NotaFiscalProduto(Entidade):
    # - Dados
    #  - Codigo (obrigatorio)
    codigo = str()

    #  - Descricao (obrigatorio)
    descricao = str()

    #  - EAN
    ean = str()

    #  - NCM
    ncm = str()

    #  - EX TIPI
    ex_tipi = str()

    #  - CFOP (obrigatorio)
    cfop = str()

    #  - Genero
    genero = str()

    #  - Unidade Comercial (obrigatorio)
    unidade_comercial = str()

    #  - Quantidade Comercial (obrigatorio)
    quantidade_comercial = Decimal()

    #  - Valor Unitario Comercial (obrigatorio)
    valor_unitario_comercial = Decimal()

    #  - Unidade Tributavel (obrigatorio)
    unidade_tributavel = str()

    #  - Quantidade Tributavel (obrigatorio)
    quantidade_tributavel = Decimal()

    #  - Valor Unitario Tributavel (obrigatorio)
    valor_unitario_tributavel = Decimal()

    #  - EAN Tributavel
    ean_tributavel = str()

    #  - Total Frete
    total_frete = Decimal()

    #  - Total Seguro
    total_seguro = Decimal()

    #  - Desconto
    desconto = Decimal()

    #  - Valor total bruto (obrigatorio)
    valor_total_bruto = Decimal()

    #  - Produto especifico (seleciona de lista) - NF_PRODUTOS_ESPECIFICOS
    produto_especifico = str()

    # - Tributos
    #  - ICMS
    #   - Situacao tributaria (obrigatorio - seleciona de lista) - ICMS_TIPOS_TRIBUTACAO
    icms_situacao_tributaria = str()

    #   - Origem (obrigatorio - seleciona de lista) - ICMS_ORIGENS
    icms_origem = int()

    #   - ICMS
    #    - Modalidade de determinacao da BC ICMS (seleciona de lista) - ICMS_MODALIDADES
    icms_modalidade_determinacao_bc = int()

    #    - Percentual reducao da BC ICMS
    icms_percentual_reducao_bc = Decimal()

    #    - Valor da base de calculo ICMS
    icms_valor_base_calculo = Decimal()

    #    - Aliquota ICMS
    icms_aliquota = Decimal()

    #    - Valor do ICMS
    icms_valor = Decimal()

    #   - ICMS ST
    #    - Modalidade de determinacao da BC ICMS ST (seleciona de lista) - ICMS_MODALIDADES
    icms_st_modalidade_determinacao_bc = str()

    #    - Percentual reducao da BC ICMS ST
    icms_st_percentual_reducao_bc = Decimal()

    #    - Valor da base de calculo ICMS ST
    icms_st_valor_base_calculo = Decimal()

    #    - Aliquota ICMS ST
    icms_st_aliquota = Decimal()

    #    - Valor do ICMS ST
    icms_st_valor = Decimal()

    #  - IPI
    #   - Situacao tributaria (seleciona de lista) - IPI_TIPOS_TRIBUTACAO
    ipi_situacao_tributaria = str()

    #   - Classe de enquadramento
    #    - A informacao para classe de enquadramento do IPI para Cigarros e Bebidas,
    #      quando aplicavel, deve ser informada utilizando a codificacao prevista nos
    #      Atos Normativos editados pela Receita Federal
    ipi_classe_enquadramento = str()

    #   - Codigo do enquadramento
    ipi_codigo_enquadramento = str()

    #   - CNPJ do Produtor
    ipi_cnpj_produtor = str()

    #   - Codigo do selo de controle
    #    - A informacao do codigo de selo, quando aplicavel, deve ser informada
    #      utilizando a codificacao prevista nos Atos Normativos editados pela Receita
    #      Federal
    ipi_codigo_selo_controle = str()

    #   - Quantidade do selo de controle
    ipi_quantidade_selo_controle = Decimal()

    #   - Tipo de calculo (seleciona de lista) - IPI_TIPOS_CALCULO
    ipi_tipo_calculo = str()

    #    - Percentual
    #     - Valor da base de calculo
    ipi_valor_base_calculo = Decimal()

    #     - Aliquota
    ipi_aliquota = Decimal()

    #    - Em valor
    #     - Quantidade total unidade padrao
    ipi_quantidade_total_unidade_padrao = Decimal()

    #     - Valor por unidade
    ipi_valor_unidade = Decimal()

    #   - Valor do IPI
    ipi_valor_ipi = Decimal()

    #  - PIS
    #   - PIS
    #    - Situacao tributaria (obrigatorio - seleciona de lista) - PIS_TIPOS_TRIBUTACAO
    pis_situacao_tributaria = str()

    #    - Tipo de calculo (seleciona de lista) - PIS_TIPOS_CALCULO
    pis_tipo_calculo = str()

    #     - Percentual
    #      - Valor da base de calculo
    pis_valor_base_calculo = Decimal()

    #      - Aliquota (percentual)
    pis_aliquota_percentual = Decimal()

    #     - Em valor
    #      - Aliquota (em reais)
    pis_aliquota_reais = Decimal()

    #      - Quantidade vendida
    pis_quantidade_vendida = Decimal()

    #    - Valor do PIS
    pis_valor = Decimal()

    #   - PIS ST
    #    - Tipo de calculo (seleciona de lista) - PIS_TIPOS_CALCULO
    pis_st_tipo_calculo = str()

    #     - Percentual
    #      - Valor da base de calculo
    pis_st_valor_base_calculo = Decimal()

    #      - Aliquota (percentual)
    pis_st_aliquota_percentual = Decimal()

    #     - Em valor
    #      - Aliquota (em reais)
    pis_st_aliquota_reais = Decimal()

    #      - Quantidade vendida
    pis_st_quantidade_vendida = Decimal()

    #    - Valor do PIS ST
    pis_st_valor = Decimal()

    #  - COFINS
    #   - COFINS
    #    - Situacao tributaria (obrigatorio - seleciona de lista) - COFINS_TIPOS_TRIBUTACAO
    cofins_situacao_tributaria = str()

    #    - Tipo de calculo (seleciona de lista) - COFINS_TIPOS_CALCULO
    cofins_tipo_calculo = str()

    #     - Percentual
    #      - Valor da base de calculo
    cofins_valor_base_calculo = Decimal()

    #      - Aliquota (percentual)
    cofins_aliquota_percentual = Decimal()

    #     - Em Valor
    #      - Aliquota (em reais)
    cofins_aliquota_reais = Decimal()

    #      - Quantidade vendida
    cofins_quantidade_vendida = Decimal()

    #    - Valor do COFINS
    cofins_valor = Decimal()

    #   - COFINS ST
    #    - Tipo de calculo (seleciona de lista) - COFINS_TIPOS_CALCULO
    cofins_st_tipo_calculo = str()

    #     - Percentual
    #      - Valor da base de calculo
    cofins_st_valor_base_calculo = Decimal()

    #      - Aliquota (percentual)
    cofins_st_aliquota_percentual = Decimal()

    #     - Em Valor
    #      - Aliquota (em reais)
    cofins_st_aliquota_reais = Decimal()

    #      - Quantidade vendida
    cofins_st_quantidade_vendida = Decimal()

    #    - Valor do COFINS ST
    cofins_st_valor = Decimal()

    #  - ISSQN
    #   - Valor da base de calculo
    issqn_valor_base_calculo = Decimal()

    #   - Aliquota
    issqn_aliquota = Decimal()

    #   - Lista de servico (seleciona de lista)
    #    - Aceita somente valores maiores que 100, disponiveis no arquivo data/ISSQN/Lista-Servicos.txt
    issqn_lista_servico = str()

    #   - UF
    issqn_uf = str()

    #   - Municipio de ocorrencia
    issqn_municipio = str()

    #   - Valor do ISSQN
    issqn_valor = Decimal()

    #  - Imposto de Importacao
    #   - Valor base de calculo
    imposto_importacao_valor_base_calculo = Decimal()

    #   - Valor despesas aduaneiras
    imposto_importacao_valor_despesas_aduaneiras = Decimal()

    #   - Valor do IOF
    imposto_importacao_valor_iof = Decimal()

    #   - Valor imposto de importacao
    imposto_importacao_valor = Decimal()

    # - Informacoes Adicionais
    #  - Texto livre de informacoes adicionais
    informacoes_adicionais = str()

    # - Declaracao de Importacao (lista 1 para * / ManyToManyField)
    declaracoes_importacao = None

    def __init__(self, *args, **kwargs):
        self.declaracoes_importacao = []

        super(NotaFiscalProduto, self).__init__(*args, **kwargs)

    def adicionar_declaracao_importacao(self, **kwargs):
        u"""Adiciona uma instancia de Declaracao de Importacao"""
        self.declaracoes_importacao.append(NotaFiscalDeclaracaoImportacao(**kwargs))

class NotaFiscalDeclaracaoImportacao(Entidade):
    #  - Numero DI/DSI/DA
    numero_di_dsi_da = str()

    #  - Data de registro
    data_registro = None

    #  - Codigo exportador
    codigo_exportador = str()

    #  - Desembaraco aduaneiro
    #   - UF
    desembaraco_aduaneiro_uf = str()

    #   - Local
    desembaraco_aduaneiro_local = str()

    #   - Data
    desembaraco_aduaneiro_data = str()

    #  - Adicoes (lista 1 para * / ManyToManyField)
    adicoes = None

    def __init__(self, *args, **kwargs):
        self.declaracoes_importacao = []

        super(NotaFiscalDeclaracaoImportacao, self).__init__(*args, **kwargs)

    def adicionar_adicao(self, **kwargs):
        u"""Adiciona uma instancia de Adicao de Declaracao de Importacao"""
        self.adicoes.append(NotaFiscalDeclaracaoImportacaoAdicao(**kwargs))

class NotaFiscalDeclaracaoImportacaoAdicao(Entidade):
    #   - Numero
    numero = str()

    #   - Desconto
    desconto = str()

    #   - Codigo fabricante
    codigo_fabricante = str()

class NotaFiscalTransporteVolume(Entidade):
    #  - Quantidade
    quantidade = Decimal()

    #  - Especie
    especie = str()

    #  - Marca
    marca = str()

    #  - Numeracao
    numeracao = str()

    #  - Peso Liquido (kg)
    peso_liquido = Decimal()

    #  - Peso Bruto (kg)
    peso_bruto = Decimal()

    #  - Lacres (lista 1 para * / ManyToManyField)
    lacres = None

    def __init__(self, *args, **kwargs):
        self.lacres = []

        super(NotaFiscalTransporteVolume, self).__init__(*args, **kwargs)

    def adicionar_lacre(self, **kwargs):
        u"""Adiciona uma instancia de Lacre de Volume de Transporte"""
        self.lacres.append(NotaFiscalTransporteVolumeLacre(**kwargs))

class NotaFiscalTransporteVolumeLacre(Entidade):
    #   - Numero de lacres
    numero_lacre = str()

class NotaFiscalCobrancaDuplicata(Entidade):
    #  - Numero
    numero = str()

    #  - Data de vencimento
    data_vencimento = None

    #  - Valor
    valor = Decimal()

class NotaFiscalObservacaoContribuinte(Entidade):
    #  - Nome do campo
    nome_campo = str()

    #  - Observacao
    observacao = str()

class NotaFiscalProcessoReferenciado(Entidade):
    #  - Identificador do processo
    identificador_processo = str()

    #  - Origem (seleciona de lista) - ORIGENS_PROCESSO
    #   - SEFAZ
    #   - Justica federal
    #   - Justica estadual
    #   - Secex/RFB
    #   - Outros
    origem = str()

class NotaFiscalEntregaRetirada(Entidade):
    # - Tipo de Documento (obrigatorio) - default CNPJ
    tipo_documento = 'CNPJ'

    # - Numero do Documento (obrigatorio)
    numero_documento = str()

    # - Endereco
    #  - Logradouro (obrigatorio)
    endereco_logradouro = str()

    #  - Numero (obrigatorio)
    endereco_numero = str()

    #  - Complemento
    endereco_complemento = str()

    #  - Bairro (obrigatorio)
    endereco_bairro = str()

    #  - CEP
    endereco_cep = str()

    #  - Pais (seleciona de lista)
    endereco_pais = CODIGO_BRASIL

    #  - UF (obrigatorio)
    endereco_uf = str()

    #  - Municipio (obrigatorio)
    endereco_municipio = str()

    #  - Telefone
    endereco_telefone = str()


########NEW FILE########
__FILENAME__ = produto
# -*- coding: utf-8 -*-
from base import Entidade
from pynfe.utils.flags import ICMS_TIPOS_TRIBUTACAO, ICMS_ORIGENS, ICMS_MODALIDADES

from decimal import Decimal

class Produto(Entidade):
    """XXX: E provavel que esta entidade sera descartada."""

    # Dados do Produto
    # - Descricao (obrigatorio)
    descricao = str()

    # - Codigo (obrigatorio) - nao pode ser alterado quando em edicao
    codigo = str()

    # - EAN
    ean = str()

    # - EAN Unid. Tributavel
    ean_unidade_tributavel = str()

    # - EX TIPI
    ex_tipi = str()

    # - Genero
    genero = str()

    # - NCM
    ncm = str()

    # - Unid. Com.
    unidade_comercial = str()

    # - Valor Unitario Com.
    valor_unitario_comercial = Decimal()

    # - Unid. Trib.
    unidade_tributavel = str()

    # - Qtd. Trib.
    quantidade_tributavel = Decimal()

    # - Valor Unitario Trib.
    valor_unitario_tributavel = Decimal()

    # Impostos
    # - ICMS (lista 1 para * / ManyToManyField)
    icms = None

    # - IPI
    #  - Classe de Enquadramento (cigarros e bebidas)
    ipi_classe_enquadramento = str()

    #  - Codigo de Enquadramento Legal
    ipi_codigo_enquadramento_legal = str()

    #  - CNPJ do Produtor
    ipi_cnpj_produtor = str()

    def __init__(self, *args, **kwargs):
        self.icms = []

        super(Produto, self).__init__(*args, **kwargs)

    def __str__(self):
        return ' '.join([self.codigo, self.descricao])

    def adicionar_icms(self, **kwargs):
        u"""Adiciona uma instancia de ICMS a lista de ICMS do produto"""
        self.icms.append(ProdutoICMS(**kwargs))

class ProdutoICMS(Entidade):
    #  - Tipo de Tributacao (seleciona de lista) - ICMS_TIPOS_TRIBUTACAO
    tipo_tributacao = str()

    #  - Origem (seleciona de lista) - ICMS_ORIGENS
    origem = str()

    #  - Modalidade de determinacao da Base de Calculo (seleciona de lista) - ICMS_MODALIDADES
    modalidade = str()

    #  - Aliquota ICMS
    aliquota = Decimal()

    #  - Percentual de reducao da Base de Calculo
    percentual_reducao = Decimal()

    #  - Modalidade de determinacao da Base de Calculo do ICMS ST (seleciona de lista) - ICMS_MODALIDADES
    st_modalidade = str()

    #  - Aliquota ICMS ST
    st_aliquota = Decimal()

    #  - Percentual de reducao do ICMS ST
    st_percentual_reducao = Decimal()

    #  - Percentual da margem de Valor Adicionado ICMS ST
    st_percentual_margem_valor_adicionado = Decimal()


########NEW FILE########
__FILENAME__ = transportadora
# -*- coding: utf-8 -*-
from base import Entidade
from pynfe.utils.flags import TIPOS_DOCUMENTO

class Transportadora(Entidade):

    # Dados da Transportadora
    # - Nome/Razão Social (obrigatorio)
    razao_social = str()

    # - Tipo de Documento (obrigatorio) - default CNPJ
    tipo_documento = 'CNPJ'

    # - Numero do Documento (obrigatorio)
    numero_documento = str()

    # - Inscricao Estadual
    inscricao_estadual = str()

    # Endereco
    # - Logradouro (obrigatorio)
    endereco_logradouro = str()

    # - UF (obrigatorio)
    endereco_uf = str()

    # - Municipio (obrigatorio)
    endereco_municipio = str()

    def __str__(self):
        return ' '.join([self.tipo_documento, self.numero_documento])


########NEW FILE########
__FILENAME__ = excecoes
class NenhumObjetoEncontrado(Exception):
    pass

class MuitosObjetosEncontrados(Exception):
    pass


########NEW FILE########
__FILENAME__ = assinatura
# -*- coding: utf-8 -*-

import xmlsec, libxml2 # FIXME: verificar ambiguidade de dependencias: lxml e libxml2

from pynfe.utils import etree, StringIO, extrair_tag
from pynfe.utils.flags import NAMESPACE_NFE, NAMESPACE_SIG

class Assinatura(object):
    """Classe abstrata responsavel por definir os metodos e logica das classes
    de assinatura digital."""

    certificado = None
    senha = None

    def __init__(self, certificado, senha):
        self.certificado = certificado
        self.senha = senha

    def assinar_arquivo(self, caminho_arquivo):
        """Efetua a assinatura dos arquivos XML informados"""
        pass

    def assinar_xml(self, xml):
        """Efetua a assinatura numa string contendo XML valido."""
        pass

    def assinar_etree(self, raiz):
        u"""Efetua a assinatura numa instancia da biblioteca lxml.etree.
        
        Este metodo de assinatura será utilizado internamente pelos demais,
        sendo que eles convertem para uma instancia lxml.etree para somente
        depois efetivar a assinatura.
        
        TODO: Verificar o funcionamento da PyXMLSec antes de efetivar isso."""
        pass

    def assinar_objetos(self, objetos):
        """Efetua a assinatura em instancias do PyNFe"""
        pass

    def verificar_arquivo(self, caminho_arquivo):
        pass

    def verificar_xml(self, xml):
        pass

    def verificar_etree(self, raiz):
        pass

    def verificar_objetos(self, objetos):
        pass

class AssinaturaA1(Assinatura):
    """Classe abstrata responsavel por efetuar a assinatura do certificado
    digital no XML informado."""
    
    def assinar_arquivo(self, caminho_arquivo, salva=True):
        # Carrega o XML do arquivo
        raiz = etree.parse(caminho_arquivo)

        # Efetua a assinatura
        xml = self.assinar_etree(raiz, retorna_xml=True)

        # Grava XML assinado no arquivo
        if salva:
            fp = file(caminho_arquivo, 'w')
            fp.write(xml)
            fp.close()

        return xml

    def assinar_xml(self, xml):
        raiz = etree.parse(StringIO(xml))

        # Efetua a assinatura
        return self.assinar_etree(raiz, retorna_xml=True)

    def assinar_etree(self, raiz, retorna_xml=False):
        # Extrai a tag do elemento raiz
        tipo = extrair_tag(raiz.getroot())

        # doctype compatível com o tipo da tag raiz
        if tipo == u'NFe':
            doctype = u'<!DOCTYPE NFe [<!ATTLIST infNFe Id ID #IMPLIED>]>'
        elif tipo == u'inutNFe':
            doctype = u'<!DOCTYPE inutNFe [<!ATTLIST infInut Id ID #IMPLIED>]>'
        elif tipo == u'cancNFe':
            doctype = u'<!DOCTYPE cancNFe [<!ATTLIST infCanc Id ID #IMPLIED>]>'
        elif tipo == u'DPEC':
            doctype = u'<!DOCTYPE DPEC [<!ATTLIST infDPEC Id ID #IMPLIED>]>'

        # Tag de assinatura
        if raiz.getroot().find('Signature') is None:
            signature = etree.Element(
                    '{%s}Signature'%NAMESPACE_SIG,
                    URI=raiz.getroot().getchildren()[0].attrib['Id'],
                    nsmap={'sig': NAMESPACE_SIG},
                    )

            signed_info = etree.SubElement(signature, '{%s}SignedInfo'%NAMESPACE_SIG)
            etree.SubElement(signed_info, 'CanonicalizationMethod', Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
            etree.SubElement(signed_info, 'SignatureMethod', Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1")

            reference = etree.SubElement(signed_info, '{%s}Reference'%NAMESPACE_SIG, URI=raiz.getroot().getchildren()[0].attrib['Id'])
            transforms = etree.SubElement(reference, 'Transforms', URI=raiz.getroot().getchildren()[0].attrib['Id'])
            etree.SubElement(transforms, 'Transform', Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature")
            etree.SubElement(transforms, 'Transform', Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
            etree.SubElement(reference, '{%s}DigestMethod'%NAMESPACE_SIG, Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
            digest_value = etree.SubElement(reference, '{%s}DigestValue'%NAMESPACE_SIG)

            signature_value = etree.SubElement(signature, '{%s}SignatureValue'%NAMESPACE_SIG)

            key_info = etree.SubElement(signature, '{%s}KeyInfo'%NAMESPACE_SIG)
            x509_data = etree.SubElement(key_info, '{%s}X509Data'%NAMESPACE_SIG)
            x509_certificate = etree.SubElement(x509_data, '{%s}X509Certificate'%NAMESPACE_SIG)

            raiz.getroot().insert(0, signature)

        # Acrescenta a tag de doctype (como o lxml nao suporta alteracao do doctype,
        # converte para string para faze-lo)
        xml = etree.tostring(raiz, xml_declaration=True, encoding='utf-8')

        if xml.find('<!DOCTYPE ') == -1:
            pos = xml.find('>') + 1
            xml = xml[:pos] + doctype + xml[pos:]
            #raiz = etree.parse(StringIO(xml))

        doc_xml, ctxt, noh_assinatura, assinador = self._antes_de_assinar_ou_verificar(raiz)
        
        # Realiza a assinatura
        assinador.sign(noh_assinatura)
    
        # Coloca na instância Signature os valores calculados
        digest_value.text = ctxt.xpathEval(u'//sig:DigestValue')[0].content.replace(u'\n', u'')
        signature_value.text = ctxt.xpathEval(u'//sig:SignatureValue')[0].content.replace(u'\n', u'')
        
        # Provavelmente retornarão vários certificados, já que o xmlsec inclui a cadeia inteira
        certificados = ctxt.xpathEval(u'//sig:X509Data/sig:X509Certificate')
        x509_certificate.text = certificados[len(certificados)-1].content.replace(u'\n', u'')
    
        resultado = assinador.status == xmlsec.DSigStatusSucceeded

        # Gera o XML para retornar
        xml = doc_xml.serialize()

        # Limpa objetos da memoria e desativa funções criptográficas
        self._depois_de_assinar_ou_verificar(doc_xml, ctxt, assinador)

        if retorna_xml:
            return xml
        else:
            return etree.parse(StringIO(xml))

    def _ativar_funcoes_criptograficas(self):
        # FIXME: descobrir forma de evitar o uso do libxml2 neste processo

        # Ativa as funções de análise de arquivos XML FIXME
        libxml2.initParser()
        libxml2.substituteEntitiesDefault(1)
        
        # Ativa as funções da API de criptografia
        xmlsec.init()
        xmlsec.cryptoAppInit(None)
        xmlsec.cryptoInit()
    
    def _desativar_funcoes_criptograficas(self):
        ''' Desativa as funções criptográficas e de análise XML
        As funções devem ser chamadas aproximadamente na ordem inversa da ativação
        '''
        
        # Shutdown xmlsec-crypto library
        xmlsec.cryptoShutdown()
        
        # Shutdown crypto library
        xmlsec.cryptoAppShutdown()
        
        # Shutdown xmlsec library
        xmlsec.shutdown()
        
        # Shutdown LibXML2 FIXME: descobrir forma de evitar o uso do libxml2 neste processo
        libxml2.cleanupParser()

    def verificar_arquivo(self, caminho_arquivo):
        # Carrega o XML do arquivo
        raiz = etree.parse(caminho_arquivo)
        return self.verificar_etree(raiz)

    def verificar_xml(self, xml):
        raiz = etree.parse(StringIO(xml))
        return self.verificar_etree(raiz)

    def verificar_etree(self, raiz):
        doc_xml, ctxt, noh_assinatura, assinador = self._antes_de_assinar_ou_verificar(raiz)

        # Verifica a assinatura
        assinador.verify(noh_assinatura)
        resultado = assinador.status == xmlsec.DSigStatusSucceeded

        # Limpa objetos da memoria e desativa funções criptográficas
        self._depois_de_assinar_ou_verificar(doc_xml, ctxt, assinador)

        return resultado

    def _antes_de_assinar_ou_verificar(self, raiz):
        # Converte etree para string
        xml = etree.tostring(raiz, xml_declaration=True, encoding='utf-8')

        # Ativa funções criptográficas
        self._ativar_funcoes_criptograficas()

        # Colocamos o texto no avaliador XML FIXME: descobrir forma de evitar o uso do libxml2 neste processo
        doc_xml = libxml2.parseMemory(xml, len(xml))
    
        # Cria o contexto para manipulação do XML via sintaxe XPATH
        ctxt = doc_xml.xpathNewContext()
        ctxt.xpathRegisterNs(u'sig', NAMESPACE_SIG)
    
        # Separa o nó da assinatura
        noh_assinatura = ctxt.xpathEval(u'//*/sig:Signature')[0]
    
        # Buscamos a chave no arquivo do certificado
        chave = xmlsec.cryptoAppKeyLoad(
                filename=str(self.certificado.caminho_arquivo),
                format=xmlsec.KeyDataFormatPkcs12,
                pwd=str(self.senha),
                pwdCallback=None,
                pwdCallbackCtx=None,
                )
    
        # Cria a variável de chamada (callable) da função de assinatura
        assinador = xmlsec.DSigCtx()
    
        # Atribui a chave ao assinador
        assinador.signKey = chave

        return doc_xml, ctxt, noh_assinatura, assinador

    def _depois_de_assinar_ou_verificar(self, doc_xml, ctxt, assinador):
        # Libera a memória do assinador; isso é necessário, pois na verdade foi feita uma chamada
        # a uma função em C cujo código não é gerenciado pelo Python
        assinador.destroy()
        ctxt.xpathFreeContext()
        doc_xml.freeDoc()

        # E, por fim, desativa todas as funções ativadas anteriormente
        self._desativar_funcoes_criptograficas()
########NEW FILE########
__FILENAME__ = comunicacao
# -*- coding: utf-8 -*-
import datetime
from httplib import HTTPSConnection, HTTPResponse

from pynfe.utils import etree, StringIO, so_numeros
from pynfe.utils.flags import NAMESPACE_NFE, NAMESPACE_SOAP, VERSAO_PADRAO
from pynfe.utils.flags import CODIGOS_ESTADOS, VERSAO_PADRAO
from assinatura import AssinaturaA1

class Comunicacao(object):
    u"""Classe abstrata responsavel por definir os metodos e logica das classes
    de comunicação com os webservices da NF-e."""

    _ambiente = 1   # 1 = Produção, 2 = Homologação
    servidor = None
    porta = 80
    certificado = None
    certificado_senha = None

    def __init__(self, servidor, porta, certificado, certificado_senha, homologacao=False):
        self.servidor = servidor
        self.porta = porta
        self.certificado = certificado
        self.certificado_senha = certificado_senha
        self._ambiente = homologacao and 2 or 1

class ComunicacaoSefaz(Comunicacao):
    u"""Classe de comunicação que segue o padrão definido para as SEFAZ dos Estados."""

    _versao = VERSAO_PADRAO
    _assinatura = AssinaturaA1
    
    def transmitir(self, nota_fiscal):
        pass

    def cancelar(self, nota_fiscal):
        pass

    def situacao_nfe(self, nota_fiscal):
        pass

    def status_servico(self):
        post = '/nfeweb/services/nfestatusservico.asmx'

        # Monta XML do corpo da requisição # FIXME
        raiz = etree.Element('teste')
        dados = etree.tostring(raiz)

        # Monta XML para envio da requisição
        xml = self._construir_xml_soap(
                metodo='nfeRecepcao2', # FIXME
                tag_metodo='nfeStatusServicoNF2', # FIXME
                cabecalho=self._cabecalho_soap(),
                dados=dados,
                )

        # Chama método que efetua a requisição POST no servidor SOAP
        retorno = self._post(post, xml, self._post_header())

        # Transforma o retorno em etree
        #retorno = etree.parse(StringIO(retorno))

        return bool(retorno)

    def consultar_cadastro(self, instancia):
        #post = '/nfeweb/services/cadconsultacadastro.asmx'
        post = '/nfeweb/services/nfeconsulta.asmx'

    def inutilizar_faixa_numeracao(self, numero_inicial, numero_final, emitente, certificado,
            senha, ano=None, serie='1', justificativa=''):
        post = '/nfeweb/services/nfestatusservico.asmx'

        # Valores default
        ano = str(ano or datetime.date.today().year)[-2:]
        uf = CODIGOS_ESTADOS[emitente.endereco_uf]
        cnpj = so_numeros(emitente.cnpj)

        # Identificador da TAG a ser assinada formada com Código da UF + Ano (2 posições) +
        #  CNPJ + modelo + série + nro inicial e nro final precedida do literal “ID”
        id_unico = 'ID%(uf)s%(ano)s%(cnpj)s%(modelo)s%(serie)s%(num_ini)s%(num_fin)s'%{
                'uf': uf,
                'ano': ano,
                'cnpj': cnpj,
                'modelo': '55',
                'serie': serie.zfill(3),
                'num_ini': str(numero_inicial).zfill(9),
                'num_fin': str(numero_final).zfill(9),
                }

        # Monta XML do corpo da requisição # FIXME
        raiz = etree.Element('inutNFe', xmlns="http://www.portalfiscal.inf.br/nfe", versao="1.07")
        inf_inut = etree.SubElement(raiz, 'infInut', Id=id_unico)
        etree.SubElement(inf_inut, 'tpAmb').text = str(self._ambiente)
        etree.SubElement(inf_inut, 'xServ').text = 'INUTILIZAR'
        etree.SubElement(inf_inut, 'cUF').text = uf
        etree.SubElement(inf_inut, 'ano').text = ano
        etree.SubElement(inf_inut, 'CNPJ').text = emitente.cnpj
        etree.SubElement(inf_inut, 'mod').text = '55'
        etree.SubElement(inf_inut, 'serie').text = serie
        etree.SubElement(inf_inut, 'nNFIni').text = str(numero_inicial)
        etree.SubElement(inf_inut, 'nNFFin').text = str(numero_final)
        etree.SubElement(inf_inut, 'xJust').text = justificativa
        #dados = etree.tostring(raiz, encoding='utf-8', xml_declaration=True)

        # Efetua assinatura
        assinatura = self._assinatura(certificado, senha)
        dados = assinatura.assinar_etree(etree.ElementTree(raiz), retorna_xml=True)

        # Monta XML para envio da requisição
        xml = self._construir_xml_soap(
                metodo='nfeRecepcao2', # XXX
                tag_metodo='nfeInutilizacaoNF', # XXX
                cabecalho=self._cabecalho_soap(),
                dados=dados,
                )

        # Chama método que efetua a requisição POST no servidor SOAP
        retorno = self._post(post, xml, self._post_header())

        # Transforma o retorno em etree # TODO
        #retorno = etree.parse(StringIO(retorno))

        return retorno

    def _cabecalho_soap(self):
        u"""Monta o XML do cabeçalho da requisição SOAP"""

        raiz = etree.Element('cabecMsg', xmlns=NAMESPACE_NFE, versao="1.02")
        etree.SubElement(raiz, 'versaoDados').text = self._versao

        return etree.tostring(raiz, encoding='utf-8', xml_declaration=True)

    def _construir_xml_soap(self, metodo, tag_metodo, cabecalho, dados):
        u"""Mota o XML para o envio via SOAP"""

        raiz = etree.Element('{%s}Envelope'%NAMESPACE_SOAP, nsmap={'soap': NAMESPACE_SOAP})

        body = etree.SubElement(raiz, '{%s}Body'%NAMESPACE_SOAP)
        met = etree.SubElement(
                body, tag_metodo, xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/%s"%metodo,
                )

        etree.SubElement(met, 'nfeCabecMsg').text = cabecalho
        etree.SubElement(met, 'nfeDadosMsg').text = dados

        return etree.tostring(raiz, encoding='utf-8', xml_declaration=True)

    def _post_header(self):
        u"""Retorna um dicionário com os atributos para o cabeçalho da requisição HTTP"""
        return {
            u'content-type': u'application/soap+xml; charset=utf-8',
            u'Accept': u'application/soap+xml; charset=utf-8',
            }

    def _post(self, post, xml, header):
        # Separa arquivos de certificado para chave e certificado (sozinho)
        caminho_chave, caminho_cert = self.certificado.separar_arquivo(senha=self.certificado_senha)

        # Abre a conexão HTTPS
        con = HTTPSConnection(self.servidor, self.porta, key_file=caminho_chave, cert_file=caminho_cert)

        try:
            #con.set_debuglevel(100)

            con.request(u'POST', post, xml, header)

            resp = con.getresponse()
        
            # Tudo certo!
            if resp.status == 200:
                return resp.read()
        finally:
            con.close()


########NEW FILE########
__FILENAME__ = danfe
class DANFE(object):
    pass


########NEW FILE########
__FILENAME__ = serializacao
# -*- coding: utf-8 -*-
try:
    set
except:
    from sets import Set as set

from pynfe.entidades import Emitente, Cliente, Produto, Transportadora, NotaFiscal
from pynfe.excecoes import NenhumObjetoEncontrado, MuitosObjetosEncontrados
from pynfe.utils import etree, so_numeros, obter_municipio_por_codigo, obter_pais_por_codigo
from pynfe.utils.flags import CODIGOS_ESTADOS, VERSAO_PADRAO

class Serializacao(object):
    """Classe abstrata responsavel por fornecer as funcionalidades basicas para
    exportacao e importacao de Notas Fiscais eletronicas para formatos serializados
    de arquivos. Como XML, JSON, binario, etc.
    
    Nao deve ser instanciada diretamente!"""

    _fonte_dados = None
    _ambiente = 1   # 1 = Produção, 2 = Homologação
    _nome_aplicacao = 'PyNFe'

    def __new__(cls, *args, **kwargs):
        if cls == Serializacao:
            raise Exception('Esta classe nao pode ser instanciada diretamente!')
        else:
            return super(Serializacao, cls).__new__(cls, *args, **kwargs)

    def __init__(self, fonte_dados, homologacao=False):
        self._fonte_dados = fonte_dados
        self._ambiente = homologacao and 2 or 1

    def exportar(self, destino, **kwargs):
        """Gera o(s) arquivo(s) de exportacao a partir da Nofa Fiscal eletronica
        ou lista delas."""

        raise Exception('Metodo nao implementado')

    def importar(self, origem):
        """Fabrica que recebe o caminho ou objeto de origem e instancia os objetos
        da PyNFe"""

        raise Exception('Metodo nao implementado')

class SerializacaoXML(Serializacao):
    _versao = VERSAO_PADRAO

    def exportar(self, destino=None, retorna_string=False, **kwargs):
        """Gera o(s) arquivo(s) de Nofa Fiscal eletronica no padrao oficial da SEFAZ
        e Receita Federal, para ser(em) enviado(s) para o webservice ou para ser(em)
        armazenado(s) em cache local."""

        # No raiz do XML de saida
        raiz = etree.Element('NFe', xmlns="http://www.portalfiscal.inf.br/nfe")

        # Carrega lista de Notas Fiscais
        notas_fiscais = self._fonte_dados.obter_lista(_classe=NotaFiscal, **kwargs)

        for nf in notas_fiscais:
            raiz.append(self._serializar_notas_fiscal(nf, retorna_string=False))

        if retorna_string:
            return etree.tostring(raiz, pretty_print=True)
        else:
            return raiz

    def importar(self, origem):
        """Cria as instancias do PyNFe a partir de arquivos XML no formato padrao da
        SEFAZ e Receita Federal."""

        raise Exception('Metodo nao implementado')

    def _serializar_emitente(self, emitente, tag_raiz='emit', retorna_string=True):
        raiz = etree.Element(tag_raiz)

        # Dados do emitente
        etree.SubElement(raiz, 'CNPJ').text = so_numeros(emitente.cnpj)
        etree.SubElement(raiz, 'xNome').text = emitente.razao_social
        etree.SubElement(raiz, 'xFant').text = emitente.nome_fantasia
        etree.SubElement(raiz, 'IE').text = emitente.inscricao_estadual

        # Endereço
        endereco = etree.SubElement(raiz, 'enderEmit')
        etree.SubElement(endereco, 'xLgr').text = emitente.endereco_logradouro
        etree.SubElement(endereco, 'nro').text = emitente.endereco_numero
        etree.SubElement(endereco, 'xCpl').text = emitente.endereco_complemento
        etree.SubElement(endereco, 'xBairro').text = emitente.endereco_bairro
        etree.SubElement(endereco, 'cMun').text = emitente.endereco_municipio
        etree.SubElement(endereco, 'xMun').text = obter_municipio_por_codigo(
                emitente.endereco_municipio, emitente.endereco_uf,
                )
        etree.SubElement(endereco, 'UF').text = emitente.endereco_uf
        etree.SubElement(endereco, 'CEP').text = so_numeros(emitente.endereco_cep)
        etree.SubElement(endereco, 'cPais').text = emitente.endereco_pais
        etree.SubElement(endereco, 'xPais').text = obter_pais_por_codigo(emitente.endereco_pais)
        etree.SubElement(endereco, 'fone').text = emitente.endereco_telefone

        if retorna_string:
            return etree.tostring(raiz, pretty_print=True)
        else:
            return raiz

    def _serializar_cliente(self, cliente, tag_raiz='dest', retorna_string=True):
        raiz = etree.Element(tag_raiz)

        # Dados do cliente
        etree.SubElement(raiz, cliente.tipo_documento).text = so_numeros(cliente.numero_documento)
        etree.SubElement(raiz, 'xNome').text = cliente.razao_social
        etree.SubElement(raiz, 'IE').text = cliente.inscricao_estadual

        # Endereço
        endereco = etree.SubElement(raiz, 'enderDest')
        etree.SubElement(endereco, 'xLgr').text = cliente.endereco_logradouro
        etree.SubElement(endereco, 'nro').text = cliente.endereco_numero
        etree.SubElement(endereco, 'xCpl').text = cliente.endereco_complemento
        etree.SubElement(endereco, 'xBairro').text = cliente.endereco_bairro
        etree.SubElement(endereco, 'cMun').text = cliente.endereco_municipio
        etree.SubElement(endereco, 'xMun').text = obter_municipio_por_codigo(
                cliente.endereco_municipio, cliente.endereco_uf,
                )
        etree.SubElement(endereco, 'UF').text = cliente.endereco_uf
        etree.SubElement(endereco, 'CEP').text = so_numeros(cliente.endereco_cep)
        etree.SubElement(endereco, 'cPais').text = cliente.endereco_pais
        etree.SubElement(endereco, 'xPais').text = obter_pais_por_codigo(cliente.endereco_pais)
        etree.SubElement(endereco, 'fone').text = cliente.endereco_telefone

        if retorna_string:
            return etree.tostring(raiz, pretty_print=True)
        else:
            return raiz

    def _serializar_transportadora(self, transportadora, tag_raiz='transporta', retorna_string=True):
        raiz = etree.Element(tag_raiz)

        # Dados da transportadora
        etree.SubElement(raiz, transportadora.tipo_documento).text = so_numeros(transportadora.numero_documento)
        etree.SubElement(raiz, 'xNome').text = transportadora.razao_social
        etree.SubElement(raiz, 'IE').text = transportadora.inscricao_estadual

        # Endereço
        etree.SubElement(raiz, 'xEnder').text = transportadora.endereco_logradouro
        etree.SubElement(raiz, 'cMun').text = transportadora.endereco_municipio
        etree.SubElement(raiz, 'xMun').text = obter_municipio_por_codigo(
                transportadora.endereco_municipio, transportadora.endereco_uf,
                )
        etree.SubElement(raiz, 'UF').text = transportadora.endereco_uf

        if retorna_string:
            return etree.tostring(raiz, pretty_print=True)
        else:
            return raiz

    def _serializar_entrega_retirada(self, entrega_retirada, tag_raiz='entrega', retorna_string=True):
        raiz = etree.Element(tag_raiz)

        # Dados da entrega/retirada
        etree.SubElement(raiz, entrega_retirada.tipo_documento).text = so_numeros(entrega_retirada.numero_documento)

        # Endereço
        etree.SubElement(raiz, 'xLgr').text = entrega_retirada.endereco_logradouro
        etree.SubElement(raiz, 'nro').text = entrega_retirada.endereco_numero
        etree.SubElement(raiz, 'xCpl').text = entrega_retirada.endereco_complemento
        etree.SubElement(raiz, 'xBairro').text = entrega_retirada.endereco_bairro
        etree.SubElement(raiz, 'cMun').text = entrega_retirada.endereco_municipio
        etree.SubElement(raiz, 'xMun').text = obter_municipio_por_codigo(
                entrega_retirada.endereco_municipio, entrega_retirada.endereco_uf,
                )
        etree.SubElement(raiz, 'UF').text = entrega_retirada.endereco_uf

        if retorna_string:
            return etree.tostring(raiz, pretty_print=True)
        else:
            return raiz

    def _serializar_produto_servico(self, produto_servico, tag_raiz='det', retorna_string=True):
        raiz = etree.Element(tag_raiz)

        # Produto
        prod = etree.SubElement(raiz, 'prod')
        etree.SubElement(prod, 'cProd').text = str(produto_servico.codigo)
        etree.SubElement(prod, 'cEAN').text = produto_servico.ean
        etree.SubElement(prod, 'xProd').text = produto_servico.descricao
        etree.SubElement(prod, 'CFOP').text = produto_servico.cfop
        etree.SubElement(prod, 'uCom').text = produto_servico.unidade_comercial
        etree.SubElement(prod, 'qCom').text = str(produto_servico.quantidade_comercial or 0)
        etree.SubElement(prod, 'vUnCom').text = str(produto_servico.valor_unitario_comercial or 0)
        etree.SubElement(prod, 'vProd').text = str(produto_servico.valor_total_bruto or 0)
        etree.SubElement(prod, 'cEANTrib').text = produto_servico.ean_tributavel
        etree.SubElement(prod, 'uTrib').text = produto_servico.unidade_tributavel
        etree.SubElement(prod, 'qTrib').text = str(produto_servico.quantidade_tributavel)
        etree.SubElement(prod, 'vUnTrib').text = str(produto_servico.valor_unitario_tributavel)

        # Imposto
        imposto = etree.SubElement(raiz, 'imposto')

        icms = etree.SubElement(imposto, 'ICMS')
        icms_item = etree.SubElement(icms, 'ICMS'+produto_servico.icms_situacao_tributaria)
        etree.SubElement(icms_item, 'orig').text = str(produto_servico.icms_origem)
        etree.SubElement(icms_item, 'CST').text = produto_servico.icms_situacao_tributaria
        etree.SubElement(icms_item, 'modBC').text = str(produto_servico.icms_modalidade_determinacao_bc)
        etree.SubElement(icms_item, 'vBC').text = str(produto_servico.icms_valor_base_calculo)
        etree.SubElement(icms_item, 'pICMS').text = str(produto_servico.icms_aliquota)
        etree.SubElement(icms_item, 'vICMS').text = str(produto_servico.icms_valor)

        pis = etree.SubElement(imposto, 'PIS')
        pis_item = etree.SubElement(pis, 'PISAliq')
        etree.SubElement(pis_item, 'CST').text = str(produto_servico.pis_situacao_tributaria)
        etree.SubElement(pis_item, 'vBC').text = str(produto_servico.pis_valor_base_calculo)
        etree.SubElement(pis_item, 'pPIS').text = str(produto_servico.pis_aliquota_percentual)
        etree.SubElement(pis_item, 'vPIS').text = str(produto_servico.pis_valor)

        cofins = etree.SubElement(imposto, 'COFINS')
        cofins_item = etree.SubElement(cofins, 'COFINSAliq')
        etree.SubElement(cofins_item, 'CST').text = str(produto_servico.cofins_situacao_tributaria)
        etree.SubElement(cofins_item, 'vBC').text = str(produto_servico.cofins_valor_base_calculo)
        etree.SubElement(cofins_item, 'pCOFINS').text = str(produto_servico.cofins_aliquota_percentual)
        etree.SubElement(cofins_item, 'vCOFINS').text = str(produto_servico.cofins_valor)

        if retorna_string:
            return etree.tostring(raiz, pretty_print=True)
        else:
            return raiz

    def _serializar_notas_fiscal(self, nota_fiscal, tag_raiz='infNFe', retorna_string=True):
        raiz = etree.Element(tag_raiz, versao=self._versao)

        # Dados da Nota Fiscal
        ide = etree.SubElement(raiz, 'ide')
        etree.SubElement(ide, 'cUF').text = CODIGOS_ESTADOS[nota_fiscal.uf]
        etree.SubElement(ide, 'cNF').text = nota_fiscal.codigo_numerico_aleatorio
        etree.SubElement(ide, 'natOp').text = nota_fiscal.natureza_operacao
        etree.SubElement(ide, 'indPag').text = str(nota_fiscal.forma_pagamento)
        etree.SubElement(ide, 'mod').text = str(nota_fiscal.modelo)
        etree.SubElement(ide, 'serie').text = nota_fiscal.serie
        etree.SubElement(ide, 'nNF').text = str(nota_fiscal.numero_nf)
        etree.SubElement(ide, 'dEmi').text = nota_fiscal.data_emissao.strftime('%Y-%m-%d')
        etree.SubElement(ide, 'dSaiEnt').text = nota_fiscal.data_saida_entrada.strftime('%Y-%m-%d')
        etree.SubElement(ide, 'tpNF').text = str(nota_fiscal.tipo_documento)
        etree.SubElement(ide, 'cMunFG').text = nota_fiscal.municipio
        etree.SubElement(ide, 'tpImp').text = str(nota_fiscal.tipo_impressao_danfe)
        etree.SubElement(ide, 'tpEmis').text = str(nota_fiscal.forma_emissao)
        etree.SubElement(ide, 'cDV').text = nota_fiscal.dv_codigo_numerico_aleatorio
        etree.SubElement(ide, 'tpAmb').text = str(self._ambiente)
        etree.SubElement(ide, 'finNFe').text = str(nota_fiscal.finalidade_emissao)
        etree.SubElement(ide, 'procEmi').text = str(nota_fiscal.processo_emissao)
        etree.SubElement(ide, 'verProc').text = '%s %s'%(self._nome_aplicacao,
                nota_fiscal.versao_processo_emissao)

        # Emitente
        raiz.append(self._serializar_emitente(nota_fiscal.emitente, retorna_string=False))

        # Destinatário
        raiz.append(self._serializar_cliente(nota_fiscal.cliente, retorna_string=False))

        # Retirada
        if nota_fiscal.retirada:
            raiz.append(self._serializar_entrega_retirada(
                nota_fiscal.retirada,
                retorna_string=False,
                tag_raiz='retirada',
                ))

        # Entrega
        if nota_fiscal.entrega:
            raiz.append(self._serializar_entrega_retirada(
                nota_fiscal.entrega,
                retorna_string=False,
                tag_raiz='entrega',
                ))

        # Itens
        for num, item in enumerate(nota_fiscal.produtos_e_servicos):
            det = self._serializar_produto_servico(item, retorna_string=False)
            det.attrib['nItem'] = str(num+1)

            raiz.append(det)

        # Totais
        total = etree.SubElement(raiz, 'total')
        icms_total = etree.SubElement(total, 'ICMSTot')
        etree.SubElement(icms_total, 'vBC').text = str(nota_fiscal.totais_icms_base_calculo)
        etree.SubElement(icms_total, 'vICMS').text = str(nota_fiscal.totais_icms_total)
        etree.SubElement(icms_total, 'vBCST').text = str(nota_fiscal.totais_icms_st_base_calculo)
        etree.SubElement(icms_total, 'vST').text = str(nota_fiscal.totais_icms_st_total)
        etree.SubElement(icms_total, 'vProd').text = str(nota_fiscal.totais_icms_total_produtos_e_servicos)
        etree.SubElement(icms_total, 'vFrete').text = str(nota_fiscal.totais_icms_total_frete)
        etree.SubElement(icms_total, 'vSeg').text = str(nota_fiscal.totais_icms_total_seguro)
        etree.SubElement(icms_total, 'vDesc').text = str(nota_fiscal.totais_icms_total_desconto)
        etree.SubElement(icms_total, 'vII').text = str(nota_fiscal.totais_icms_total_ii)
        etree.SubElement(icms_total, 'vIPI').text = str(nota_fiscal.totais_icms_total_ipi)
        etree.SubElement(icms_total, 'vPIS').text = str(nota_fiscal.totais_icms_pis)
        etree.SubElement(icms_total, 'vCOFINS').text = str(nota_fiscal.totais_icms_cofins)
        etree.SubElement(icms_total, 'vOutro').text = str(nota_fiscal.totais_icms_outras_despesas_acessorias)
        etree.SubElement(icms_total, 'vNF').text = str(nota_fiscal.totais_icms_total_nota)

        # Transporte
        transp = etree.SubElement(raiz, 'transp')
        etree.SubElement(transp, 'modFrete').text = str(nota_fiscal.transporte_modalidade_frete)
        
        # Transportadora
        transp.append(self._serializar_transportadora(
            nota_fiscal.transporte_transportadora,
            retorna_string=False,
            ))

        # Veículo
        veiculo = etree.SubElement(transp, 'veicTransp')
        etree.SubElement(veiculo, 'placa').text = nota_fiscal.transporte_veiculo_placa
        etree.SubElement(veiculo, 'UF').text = nota_fiscal.transporte_veiculo_uf
        etree.SubElement(veiculo, 'RNTC').text = nota_fiscal.transporte_veiculo_rntc

        # Reboque
        reboque = etree.SubElement(transp, 'reboque')
        etree.SubElement(reboque, 'placa').text = nota_fiscal.transporte_reboque_placa
        etree.SubElement(reboque, 'UF').text = nota_fiscal.transporte_reboque_uf
        etree.SubElement(reboque, 'RNTC').text = nota_fiscal.transporte_reboque_rntc

        # Volumes
        for volume in nota_fiscal.transporte_volumes:
            vol = etree.SubElement(transp, 'vol')
            etree.SubElement(vol, 'qVol').text = str(volume.quantidade)
            etree.SubElement(vol, 'esp').text = volume.especie
            etree.SubElement(vol, 'marca').text = volume.marca
            etree.SubElement(vol, 'nVol').text = volume.numeracao
            etree.SubElement(vol, 'pesoL').text = str(volume.peso_liquido)
            etree.SubElement(vol, 'pesoB').text = str(volume.peso_bruto)

            # Lacres
            lacres = etree.SubElement(vol, 'lacres')
            for lacre in volume.lacres:
                etree.SubElement(lacres, 'nLacre').text = lacre.numero_lacre

        # Informações adicionais
        info_ad = etree.SubElement(raiz, 'infAdic')
        etree.SubElement(info_ad, 'infAdFisco').text = nota_fiscal.informacoes_adicionais_interesse_fisco
        etree.SubElement(info_ad, 'infCpl').text = nota_fiscal.informacoes_complementares_interesse_contribuinte

        # 'Id' da tag raiz
        # Ex.: NFe35080599999090910270550010000000011518005123
        raiz.attrib['Id'] = nota_fiscal.identificador_unico

        if retorna_string:
            return etree.tostring(raiz, pretty_print=True)
        else:
            return raiz


########NEW FILE########
__FILENAME__ = validacao
#-*- coding:utf-8 -*-

from os import path

try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5 - cElementTree
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5 - ElementTree
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # Instalacao normal do cElementTree
                import cElementTree as etree
            except ImportError:
                try:
                    # Instalacao normal do ElementTree
                    import elementtree.ElementTree as etree
                except ImportError:
                    raise Exception('Falhou ao importar lxml/ElementTree')

XSD_FOLDER = "pynfe/data/XSDs/"

XSD_NFE="nfe_v1.10.xsd"
XSD_NFE_PROCESSADA="procNFe_v1.10.xsd"
XSD_PD_CANCELAR_NFE="procCancNFe_v1.07.xsd"
XSD_PD_INUTILIZAR_NFE="procInutNFe_v1.07.xsd"

def get_xsd(xsd_file):
    """Retorna o caminho absoluto para um arquivo xsd.
    Argumentos:
        xsd_file - nome do arquivo xsd (utilizar nomes definidos em validacao.py)
    """
    return path.abspath(path.join(XSD_FOLDER, xsd_file))

class Validacao(object):
    '''Valida documentos xml a partir do xsd informado.'''
    
    def __init__(self):
        self.clear_cache()
    
    def clear_cache(self):
        self.MEM_CACHE = {}
    
    def validar_xml(self, xml_path, xsd_file, use_assert=False):
        '''Valida um arquivo xml.
        Argumentos:
            xml_path - caminho para arquivo xml
            xsd_file - caminho para o arquivo xsd
            use_assert - levantar exceção caso documento não valide?
        '''
        return self.validar_etree(etree.parse(xml_path), xsd_file, use_assert)
    
    def validar_etree(self, xml_doc, xsd_file, use_assert=False):
        '''Valida um documento lxml diretamente.
        Argumentos:
            xml_doc - documento etree
            xsd_file - caminho para o arquivo xsd
            use_assert - levantar exceção caso documento não valide?
        '''
        xsd_filepath = get_xsd(xsd_file)
        
        try:
            # checa se o schema ja existe no cache
            xsd_schema = self.MEM_CACHE[xsd_filepath]
        except:
            # lê xsd e atualiza cache
            xsd_doc = etree.parse(xsd_filepath)
            xsd_schema = etree.XMLSchema(xsd_doc)
            self.MEM_CACHE[xsd_file] = xsd_schema
        return use_assert and xsd_schema.assertValid(xml_doc) \
               or xsd_schema.validate(xml_doc)
########NEW FILE########
__FILENAME__ = bar_code_128
"""
Source: http://barcode128.blogspot.com/2007/03/code128py.html

This class generate code 128 (http://en.wikipedia.org/wiki/Code_128) bar code, 
it requires PIL (python imaging library) installed.

This program is based on EanBarCode.py found on 
http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/426069 submitted by Remi Inconnu.

Code 128 is variable lenght and a 103 module checksum is added automatically.

Create bar code sample :
   from Code128 import Code128
   bar = Code128()
   bar.getImage("9782212110708",50,"gif")
"""

# courbB08.pil PIL Font file uuencoded
courB08_pil ="""eJztl91rFkcUxp+Zt7vGFYzVtiJKICgYlLRWkaBBVGgDraFGCH5gsQp+QMBqabAVRYJYAlakCkoh
CpYgxaLkIu1NvLBeSAStglpqL6xQAsVe2AuL5u2buH3mzGaYPf9AKWTl8d3nl7MzZ2bnazvea9+9
7+PurFWut5e0Zu+s7VybYfKavP7LK3X/5TlM4Q3/OWbyf1ARD/6mgb2SjwtPhbpnq0iKZ6ahrmCj
wqbxdgamRnHOA69jimN5zvIS8cDcUEeVdYzRAw1FHcJYXgPvG4s6Jlgj7xeEequS3wLeNvGvnrEO
tq+Jt82szT+b86+WHlgS2jHGuHF6YHnog1zaupxqCcy3t4X3rVG9iXhgjW+bsFQ80BaxRDywTrF1
VId6toPaqOI2UlsV20ptV2w7tUuxXVSXYl3UvoIZ9kFFPPBJ6D/HLD3QXbwjyDjI6YHPiz5FXiN7
SQ8cDu/N9/1h3veEOP/Oe6gvQnmuvYYe+NL3qYyNVDxw2seF8XKa+jrKJREPnFdx56l+xfqpS4pd
ogZUeQPU91FcKh64GveBeOCaKu8adUM9e4O6reJuU/cUu0c9VM8+pB6r/B5TI+rZEerPUpyhB/6K
5lsqHniuyntO1VR5Nb5CU86FHqZOsTqqXrF66o2ojlQ8zDwVN4+aX86FHqYpXg9YLeevWRzPc7LF
ZG+V1wN6mKXxvMzH6GFaJua5zGNLD7MqmtNcc+hh1oT1oCb5cf6aNj92mbPMGXqY9jCPasLaqQ1h
jMv8pYfZpOI2UR9GcYl4mB1RnMtvB9me8N583B5qb3mNoIf5NGJc1+hhPvPrrjybioc5op49Qh0L
dfj8jlHHQ3s9O059Fc3zRDzMmVKcpYfpU+3oI/umxJyH+TYqLxUPc0X13xVqMMovFQ8zpPIbon6M
WCoeZljVMUz9VIqz9DAP1Dt6QP0a9gpZ7+lhHhXjysreaOhhfiv1vaGH+T2Mv5rbU+hh/uAaOnlN
Xv+Hy4/7mtv3OW5hnpTODIYe5mm0xqbiYf4OcbLv08NU1ZyuuqKLOEvm6sjhJkd8TjRustgkrO3u
vFGjh60r1uyiPHrY6eH84tb7l/SwM8vrAT3snHgNY9wcsoby+Y8edn5UxxTxsIuitrlcFpG9GcVx
/6CHXRrKk72MHrYl3stYB/ceu7I4X02wlWSrCmaF1ehhV7NrovWKHrattI4betj20Fc8r7E87kf2
g+gcy32BHnZDfKZmHPco2xnl4vqlk2yz6r/N1EfRPpiKh90d7VGpeNi9inGPst2lNdbSwx4McS8k
7iDVE/Ytz3qoXsV6qZOKnaTOBDYqjPuRPRfOkz7uHNUf4uQMQg/7XekMYulhB6JnE/GwP0T1JuJh
ryrGM6G9HuWSiIcdDnPmhTs70sPeCuPes1vUXcXuUvcDGxV2n/olOisn4mEfhfOVby/3KDsSlZeI
h32iGOe0faoY57R9ptgzajTKJREPOx7aJnOfHhUbxov0Mz0qU8v50aMyo/wu6VGZrdhsqqH8fnll
HEEz4zj6DNMxK+4X+gyv8cszyoU+4zfmjNAO9zuXrNGXF1gj2ULFFpI1K9ZMtiww//22jGwFXg39
535XkK0O+cl5gz7Du6iP5wd9hvfDs9LP9BnWR/U6tp6sU7FOsi1RLo5tIdsWled+t5HtVO3YSdal
WBfZftW2/WQHVH4HyA6F9+GfPUR2VOV3lKxXsV6yE4qdIDul2Cmys6ptZ8n6Qi7+m7OP7ELoU/8t
dIHsoo8L+V0ku6xyvkw2qNgg2VBgvg+GyK6XyrP0GW5ydE3EuXd5k+xOeOdVibtD9jNm/Qv15O4i"""

# courbB08.pbm font file uuencoded
courB08_pbm ="""eJxNkntM01cUx8+P2/1apUAZEpECq4KRjKhF0E55FYEp4yG6mglz2Q8Q1BhERhhls/zKI+CID4wb
IAPKpk4GAzqZPKKMX2GIUwGJG+ImtKwKjIzXcGuBtncV0Hn+uLnn5Nzv55xv7mdRkbusVjquBACr
0N3B+wCQi/m+ijAf4LGl/wgAiwkNDpRIyyABSjGkBQ/fa3c1bfLs4U8ulDcYUs/502rTpIlO9pyc
Kp/Buql6f3rmZ1NqvpO2SZXf0duY3j0563zjoZpW8AvHRmVeZ/Co36mFR8bERzlsxOMJ+oJshsS5
7rlfzFzmnZFEFnIEZjTGizgLsLzjl4QtrNprBRu10e+u9GgePHjG63bPDw/H87uix0Vtsvkqg9qO
lUimPLiOM4z69YfqIu5Pa2Sr/io6n9Xmf9e+57W1Iapo4lLQBdLSWc/z3KOSlgznDXTW/Flh21kX
IeUIX8FZVL9dwP4NBH5jglYxkBNFmWgMcfsAxM/9gEL5TTwYpnfElR8qQ+WiCgeTHOAfb2bW/cQC
/FozFOOQzAebtjRvQLI7HBtXvaZe25a3Q/1vZpPa+kd1XXKuflr5Cm48YUsUcjMXjsm/sf+22s6z
QAbGZ8mEXMzSE4y9AHhRpltwB1N9ynz5H2MOi0MEi4E5O1ov9ogrFU5cMWAcdgQb3xHFtFK+0pkh
VnYWxltx92j69p6jJ9OnHr+Cq5x5X6Mz70JcX2tEG5LIShM4EHIGoLIRsHzcvEuGwMYA4DZPn7gP
MA1QIgltnt82cTu7j5n76mmz3TU5Bh3PFRTHku52aBgaTnJD7m1c0a3hNjbWWjBtMsP/OFac/LYA
NAAWepdYodB58NBFIuOjNSQ4cgXplqP2RyOe8fd999T8weqBRwLwNFdQobHgA1/YTV8PH+TwV59v
Bo7Y1J4rmHFv3T9e8rmmXdGSuPpSbBnhYJ7V8ICz6AfGcdTpRkpCUU8WcOT8wb+dSHIb6QZapx0M
Y2DO4i7jYV2AUNkkErpQFHVYmFRmYD7OJhDyQSiow4IkrS3TbpQqFA9slE4jnj6peXMTC+N8buJ2
0Uv5eOothuGIiluyCDtff3miBzJHjncOIC3bPT8FLabRPd0TCWy346Mmn9Rz23WyNMJcsnqhQani
3CMFOZuYU7c20zTNVqNbGPNxALWnybeLEcTvXWpc10leI5ae/CI9qBqI686cnO6P6F33e2vAp0nz
9+hnbNeueh/261UJK5aVeSf73ZSXA7dOBXvkXODEb9hVww4KtPNAbPvaZbi0q9kICCl+CiBJSzLv
a8TlntYlC4UHvCRTlaXOy13VAbN0eae2v3hNesWXLsWPkjfOPq7e6zd1fOfc1TckDaylrvleinnT
8Ui87ScLMVhhEx7SUJ8U2zKrRR2Z1dEqZlkr7kDTuhFjpkvse9ZXN0R9H+DlYA4TXVm6/kXDQMyT
eGnJFXlLlSgva5iLUEcbiyDzNqf4Wr9kKYVUIcY40DrnsW4E4zW9QxnHVYx+bo64mIskDWjZgCrq
eVQFrS7Sh/uFLftIidKWbgj6Oq652d4c3v88Dw2JDK7bSWX/ByuaLZI="""

class Code128:
   CharSetA =  {
                ' ':0, '!':1, '"':2, '#':3, '$':4, '%':5, '&':6, "'":7,
                '(':8, ')':9, '*':10, '+':11, ',':12, '-':13, '.':14, '/':15,
                '0':16, '1':17, '2':18, '3':19, '4':20, '5':21, '6':22, '7':23,
                '8':24, '9':25, ':':26, ';':27, '<':28, '=':29, '>':30, '?':31,
                '@':32, 'A':33, 'B':34, 'C':35, 'D':36, 'E':37, 'F':38, 'G':39,
                'H':40, 'I':41, 'J':42, 'K':43, 'L':44, 'M':45, 'N':46, 'O':47,
                'P':48, 'Q':49, 'R':50, 'S':51, 'T':52, 'U':53, 'V':54, 'W':55,
                'X':56, 'Y':57, 'Z':58, '[':59, '\\':60, ']':61, '^':62, '_':63,
                '\x00':64, '\x01':65, '\x02':66, '\x03':67, '\x04':68, '\x05':69, '\x06':70, '\x07':71,
                '\x08':72, '\x09':73, '\x0A':74, '\x0B':75, '\x0C':76, '\x0D':77, '\x0E':78, '\x0F':79,
                '\x10':80, '\x11':81, '\x12':82, '\x13':83, '\x14':84, '\x15':85, '\x16':86, '\x17':87,
                '\x18':88, '\x19':89, '\x1A':90, '\x1B':91, '\x1C':92, '\x1D':93, '\x1E':94, '\x1F':95,
                'FNC3':96, 'FNC2':97, 'SHIFT':98, 'Code C':99, 'Code B':100, 'FNC4':101, 'FNC1':102, 'START A':103,
                'START B':104, 'START C':105, 'STOP':106
           }

   CharSetB = {
                ' ':0, '!':1, '"':2, '#':3, '$':4, '%':5, '&':6, "'":7,
                '(':8, ')':9, '*':10, '+':11, ',':12, '-':13, '.':14, '/':15,
                '0':16, '1':17, '2':18, '3':19, '4':20, '5':21, '6':22, '7':23,
                '8':24, '9':25, ':':26, ';':27, '<':28, '=':29, '>':30, '?':31,
                '@':32, 'A':33, 'B':34, 'C':35, 'D':36, 'E':37, 'F':38, 'G':39,
                'H':40, 'I':41, 'J':42, 'K':43, 'L':44, 'M':45, 'N':46, 'O':47,
                'P':48, 'Q':49, 'R':50, 'S':51, 'T':52, 'U':53, 'V':54, 'W':55,
                'X':56, 'Y':57, 'Z':58, '[':59, '\\':60, ']':61, '^':62, '_':63,
                '' :64, 'a':65, 'b':66, 'c':67, 'd':68, 'e':69, 'f':70, 'g':71,
                'h':72, 'i':73, 'j':74, 'k':75, 'l':76, 'm':77, 'n':78, 'o':79,
                'p':80, 'q':81, 'r':82, 's':83, 't':84, 'u':85, 'v':86, 'w':87,
                'x':88, 'y':89, 'z':90, '{':91, '|':92, '}':93, '~':94, '\x7F':95,
                'FNC3':96, 'FNC2':97, 'SHIFT':98, 'Code C':99, 'FNC4':100, 'Code A':101, 'FNC1':102, 'START A':103,
                'START B':104, 'START C':105, 'STOP':106
           }

   CharSetC = {
                '00':0, '01':1, '02':2, '03':3, '04':4, '05':5, '06':6, '07':7,
                '08':8, '09':9, '10':10, '11':11, '12':12, '13':13, '14':14, '15':15,
                '16':16, '17':17, '18':18, '19':19, '20':20, '21':21, '22':22, '23':23,
                '24':24, '25':25, '26':26, '27':27, '28':28, '29':29, '30':30, '31':31,
                '32':32, '33':33, '34':34, '35':35, '36':36, '37':37, '38':38, '39':39,
                '40':40, '41':41, '42':42, '43':43, '44':44, '45':45, '46':46, '47':47,
                '48':48, '49':49, '50':50, '51':51, '52':52, '53':53, '54':54, '55':55,
                '56':56, '57':57, '58':58, '59':59, '60':60, '61':61, '62':62, '63':63,
                '64':64, '65':65, '66':66, '67':67, '68':68, '69':69, '70':70, '71':71,
                '72':72, '73':73, '74':74, '75':75, '76':76, '77':77, '78':78, '79':79,
                '80':80, '81':81, '82':82, '83':83, '84':84, '85':85, '86':86, '87':87,
                '88':88, '89':89, '90':90, '91':91, '92':92, '93':93, '94':94, '95':95,
                '96':96, '97':97, '98':98, '99':99, 'Code B':100, 'Code A':101, 'FNC1':102, 'START A':103,
                'START B':104, 'START C':105, 'STOP':106
           }


   ValueEncodings = {  0:'11011001100',  1:'11001101100',  2:'11001100110', 
        3:'10010011000',  4:'10010001100',  5:'10001001100',
        6:'10011001000',  7:'10011000100',  8:'10001100100',
        9:'11001001000', 10:'11001000100', 11:'11000100100',
        12:'10110011100', 13:'10011011100', 14:'10011001110',
        15:'10111001100', 16:'10011101100', 17:'10011100110',
        18:'11001110010', 19:'11001011100', 20:'11001001110',
        21:'11011100100', 22:'11001110100', 23:'11101101110',
        24:'11101001100', 25:'11100101100', 26:'11100100110',
        27:'11101100100', 28:'11100110100', 29:'11100110010',
        30:'11011011000', 31:'11011000110', 32:'11000110110',
        33:'10100011000', 34:'10001011000', 35:'10001000110',
        36:'10110001000', 37:'10001101000', 38:'10001100010',
        39:'11010001000', 40:'11000101000', 41:'11000100010',
        42:'10110111000', 43:'10110001110', 44:'10001101110',
        45:'10111011000', 46:'10111000110', 47:'10001110110',
        48:'11101110110', 49:'11010001110', 50:'11000101110',
        51:'11011101000', 52:'11011100010', 53:'11011101110',
        54:'11101011000', 55:'11101000110', 56:'11100010110',
        57:'11101101000', 58:'11101100010', 59:'11100011010',
        60:'11101111010', 61:'11001000010', 62:'11110001010',
        63:'10100110000', 64:'10100001100', 65:'10010110000',
        66:'10010000110', 67:'10000101100', 68:'10000100110',
        69:'10110010000', 70:'10110000100', 71:'10011010000',
        72:'10011000010', 73:'10000110100', 74:'10000110010',
        75:'11000010010', 76:'11001010000', 77:'11110111010',
        78:'11000010100', 79:'10001111010', 80:'10100111100',
        81:'10010111100', 82:'10010011110', 83:'10111100100',
        84:'10011110100', 85:'10011110010', 86:'11110100100',
        87:'11110010100', 88:'11110010010', 89:'11011011110',
        90:'11011110110', 91:'11110110110', 92:'10101111000',
        93:'10100011110', 94:'10001011110', 95:'10111101000',
        96:'10111100010', 97:'11110101000', 98:'11110100010',
        99:'10111011110',100:'10111101110',101:'11101011110',
        102:'11110101110',103:'11010000100',104:'11010010000',
        105:'11010011100',106:'11000111010'
                        }

   def makeCode(self, code):
      """ Create the binary code
      return a string which contains "0" for white bar, "1" for black bar """
      
      current_charset = None
      pos=sum=0
      skip=False
      for c in range(len(code)):
          if skip:
              skip=False
              continue
        
          #Only switch to char set C if next four chars are digits
          if len(code[c:]) >=4 and code[c:c+4].isdigit() and current_charset!=self.CharSetC or \
             len(code[c:]) >=2 and code[c:c+2].isdigit() and current_charset==self.CharSetC:     
             #If char set C = current and next two chars ar digits, keep C 
             if current_charset!=self.CharSetC:
                 #Switching to Character set C
                 if pos:
                     strCode += self.ValueEncodings[current_charset['Code C']]
                     sum  += pos * current_charset['Code C']
                 else:
                     strCode= self.ValueEncodings[self.CharSetC['START C']]
                     sum = self.CharSetC['START C']
                 current_charset= self.CharSetC
                 pos+=1
          elif self.CharSetB.has_key(code[c]) and current_charset!=self.CharSetB and \
               not(self.CharSetA.has_key(code[c]) and current_charset==self.CharSetA): 
             #If char in chrset A = current, then just keep that
             # Switching to Character set B
             if pos:
                 strCode += self.ValueEncodings[current_charset['Code B']]
                 sum  += pos * current_charset['Code B']
             else:
                 strCode= self.ValueEncodings[self.CharSetB['START B']]
                 sum = self.CharSetB['START B']
             current_charset= self.CharSetB
             pos+=1
          elif self.CharSetA.has_key(code[c]) and current_charset!=self.CharSetA and \
               not(self.CharSetB.has_key(code[c]) and current_charset==self.CharSetB): 
             # if char in chrset B== current, then just keep that
             # Switching to Character set A
             if pos:
                 strCode += self.ValueEncodings[current_charset['Code A']]
                 sum  += pos * current_charset['Code A']
             else:
                 strCode += self.ValueEncodings[self.CharSetA['START A']]
                 sum = self.CharSetA['START A']
             current_charset= self.CharSetA
             pos+=1

          if current_charset==self.CharSetC:
             val= self.CharSetC[code[c:c+2]]
             skip=True
          else:
             val=current_charset[code[c]]

          sum += pos * val
          strCode += self.ValueEncodings[val]
          pos+=1
                        
      #Checksum
      checksum= sum % 103
            
      strCode +=  self.ValueEncodings[checksum]
                    
      #The stop character
      strCode += self.ValueEncodings[current_charset['STOP']]
                    
      #Termination bar
      strCode += "11"
            
      return strCode

   def getImage(self, value, height = 50, extension = "PNG"):
      """ Get an image with PIL library 
      value code barre value
      height height in pixel of the bar code
      extension image file extension"""
      import Image, ImageFont, ImageDraw
      from string import lower, upper
      
      # Create a missing font file
      decodeFontFile(courB08_pil ,"courB08.pil")
      decodeFontFile(courB08_pbm ,"courB08.pbm")
      
      # Get the bar code list
      bits = self.makeCode(value)
      
      # Create a new image
      position = 8
      im = Image.new("1",(len(bits)+position,height))
      
      # Load font
      font = ImageFont.load("courB08.pil")
      
      # Create drawer
      draw = ImageDraw.Draw(im)
      
      # Erase image
      draw.rectangle(((0,0),(im.size[0],im.size[1])),fill=256)
      
      # Draw text
      draw.text((0, height-9), value, font=font, fill=0)
      
      # Draw the bar codes
      for bit in range(len(bits)):
         if bits[bit] == '1':
            draw.rectangle(((bit+position,0),(bit+position,height-10)),fill=0)
            
      # Save the result image
      im.save(value+"."+lower(extension), upper(extension))


def decodeFontFile(data, file):
   """ Decode font file embedded in this script and create file """
   from zlib import decompress
   from base64 import decodestring
   from os.path import exists
   
   # If the font file is missing
   if not exists(file):
      # Write font file
      open (file, "wb").write(decompress(decodestring(data)))

def testWithChecksum():
   """ Test bar code with checksum """
   bar = Code128()
   assert(bar.makeCode('HI345678')=='11010010000110001010001100010001010111011110100010110001110001011011000010100100001001101100011101011')

def testImage():
   """ Test images generation with PIL """
   bar = Code128()
   bar.getImage("9782212110708",50,"gif")
   bar.getImage("978221211070",50,"png")

def test():
   """ Execute all tests """
   testWithChecksum()
   testImage()

if __name__ == "__main__":
   test()


########NEW FILE########
__FILENAME__ = flags
# -*- coding: utf-8 -*-

NAMESPACE_NFE = 'http://www.portalfiscal.inf.br/nfe'
NAMESPACE_SIG = 'http://www.w3.org/2000/09/xmldsig#'
NAMESPACE_SOAP = 'http://www.w3.org/2003/05/soap-envelope'

VERSAO_PADRAO = '1.01'

TIPOS_DOCUMENTO = (
    'CNPJ',
    'CPF',
)

ICMS_TIPOS_TRIBUTACAO = (
    ('00', 'ICMS 00 - Tributada integralmente'),
    ('10', 'ICMS 10 - Tributada com cobranca do ICMS por substituicao tributaria'),
    ('20', 'ICMS 20 - Com reducao da base de calculo'),
    ('30', 'ICMS 30 - Isenta ou nao tributada e com cobranca do ICMS por substituicao tributaria'),
    ('40', 'ICMS 40 - Isenta'),
    ('41', 'ICMS 41 - Nao tributada'),
    ('50', 'ICMS 50 - Suspensao'),
    ('51', 'ICMS 51 - Diferimento'),
    ('60', 'ICMS 60 - Cobrado anteriormente por substituicao tributaria'),
    ('70', 'ICMS 70 - Com reducao da base de calculo e cobranca do ICMS por substituicao tributaria'),
    ('90', 'ICMS 90 - Outras'),
)

ICMS_ORIGENS = (
    (0, 'Nacional'),
    (1, 'Estrangeira - Importacao Direta'),
    (2, 'Estrangeira - Adquirida no Mercado Interno'),
)

ICMS_MODALIDADES = (
    (0, 'Margem Valor Agregado'),
    (1, 'Pauta (valor)'),
    (2, 'Preco Tabelado Max. (valor)'),
    (3, 'Valor da Operacao'),
)

NF_STATUS = (
    'Em Digitacao',
    'Validada',
    'Assinada',
    'Em processamento',
    'Autorizada',
    'Rejeitada',
    'Cancelada',
)

NF_TIPOS_DOCUMENTO = (
    (0, 'Entrada'),
    (1, 'Saida'),
)

NF_PROCESSOS_EMISSAO = (
    (0, u'Emissão de NF-e com aplicativo do contribuinte'),
    (1, u'Emissão de NF-e avulsa pelo Fisco'),
    (2, u'Emissão de NF-e avulsa, pelo contribuinte com seu certificado digital, através do site do Fisco'),
    (3, u'Emissão NF-e pelo contribuinte com aplicativo fornecido pelo Fisco'),
)

NF_TIPOS_IMPRESSAO_DANFE = (
    (1, 'Retrato'),
    (2, 'Paisagem'),
)

NF_FORMAS_PAGAMENTO = (
    (0, 'Pagamento a vista'),
    (1, 'Pagamento a prazo'),
    (2, 'Outros'),
)

NF_FORMAS_EMISSAO = (
    (1, 'Normal'),
    (2, 'Contingencia'),
    (3, 'Contingencia com SCAN'),
    (4, 'Contingencia via DPEC'),
    (5, 'Contingencia FS-DA'),
)

NF_FINALIDADES_EMISSAO = (
    (1, 'NF-e normal'),
    (2, 'NF-e complementar'),
    (3, 'NF-e de ajuste'),
)

NF_REFERENCIADA_TIPOS = (
    'Nota Fiscal eletronica',
    'Nota Fiscal',
)

NF_PRODUTOS_ESPECIFICOS = (
    'Veiculo',
    'Medicamento',
    'Armamento',
    'Combustivel',
)

NF_AMBIENTES = (
    (1, 'Producao'),
    (2, 'Homologacao'),
)

IPI_TIPOS_TRIBUTACAO = (
    ('00', 'IPI 00 - Entrada com recuperacao de credito'),
    ('01', 'IPI 01 - Entrada tributada com aliquota zero'),
    ('02', 'IPI 02 - Entrada isenta'),
    ('03', 'IPI 03 - Entrada nao-tributada'),
    ('04', 'IPI 04 - Entrada imune'),
    ('05', 'IPI 05 - Entrada com suspensao'),
    ('49', 'IPI 49 - Outras entradas'),
    ('50', 'IPI 50 - Saida tributada'),
    ('51', 'IPI 51 - Saida tributada com aliquota zero'),
    ('52', 'IPI 52 - Saida isenta'),
    ('53', 'IPI 53 - Saida nao-tributada'),
    ('54', 'IPI 54 - Saida imune'),
    ('55', 'IPI 55 - Saida com suspensao'),
    ('99', 'IPI 99 - Outas saidas'),
)

IPI_TIPOS_CALCULO = (
    'Percentual',
    'Em Valor',
)

PIS_TIPOS_TRIBUTACAO = (
    ('01', 'PIS 01 - Operacao Tributavel - Base de Calculo = Valor da Operacao Aliquota...'), # FIXME
    ('02', 'PIS 02 - Operacao Tributavel - Base de Calculo = Valor da Operacao (Aliquota...'), # FIXME
    ('03', 'PIS 03 - Operacao Tributavel - Base de Calculo = Quantidade Vendida x Aliquota...'), # FIXME
    ('04', 'PIS 04 - Operacao Tributavel - Tributacao Monofasica - (Aliquota Zero)'),
    ('06', 'PIS 06 - Operacao Tributavel - Aliquota Zero'),
    ('07', 'PIS 07 - Operacao Isenta da Contribuicao'),
    ('08', 'PIS 08 - Operacao sem Indidencia da Contribuicao'),
    ('09', 'PIS 09 - Operacao com Suspensao da Contribuicao'),
    ('99', 'PIS 99 - Outras operacoes'),
)

PIS_TIPOS_CALCULO = IPI_TIPOS_CALCULO

COFINS_TIPOS_TRIBUTACAO = (
    ('00', 'COFINS 01 - Operacao Tributavel - Base de Calculo = Valor da Operacao Aliquota...'), # FIXME
    ('02', 'COFINS 02 - Operacao Tributavel - Base de Calculo = Valor da Operacao (Aliquota...'), # FIXME
    ('03', 'COFINS 03 - Operacao Tributavel - Base de Calculo = Quantidade Vendida x Aliquota...'), # FIXME
    ('04', 'COFINS 04 - Operacao Tributavel - Tributacao Monofasica - (Aliquota Zero)'),
    ('06', 'COFINS 06 - Operacao Tributavel - Aliquota Zero'),
    ('07', 'COFINS 07 - Operacao Isenta da Contribuicao'),
    ('08', 'COFINS 08 - Operacao sem Indidencia da Contribuicao'),
    ('09', 'COFINS 09 - Operacao com Suspensao da Contribuicao'),
    ('99', 'COFINS 99 - Outras operacoes'),
)

COFINS_TIPOS_CALCULO = IPI_TIPOS_CALCULO

MODALIDADES_FRETE = (
    (0, '0 - Por conta do emitente'),
    (1, '1 - Por conta do destinatario'),
)

ORIGENS_PROCESSO = (
    'SEFAZ',
    'Justica federal',
    'Justica estadual',
    'Secex/RFB',
    'Outros',
)

CODIGO_BRASIL = '1058'

CODIGOS_ESTADOS = {
    'RO': '11',
    'AC': '12',
    'AM': '13',
    'RR': '14',
    'PA': '15',
    'AP': '16',
    'TO': '17',
    'MA': '21',
    'PI': '22',
    'CE': '23',
    'RN': '24',
    'PB': '25',
    'PE': '26',
    'AL': '27',
    'SE': '28',
    'BA': '29',
    'MG': '31',
    'ES': '32',
    'RJ': '33',
    'SP': '35',
    'PR': '41',
    'SC': '42',
    'RS': '43',
    'MS': '50',
    'MT': '51',
    'GO': '52',
    'DF': '53',
}



########NEW FILE########
__FILENAME__ = run_fake_soap_server
# -*- coding: utf-8 -*-

"""Este script deve ser executado com Python 2.6+ e OpenSSL"""

import os, datetime

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

#from soaplib.wsgi_soap import SimpleWSGISoapApp
#from soaplib.service import soapmethod
#from soaplib.serializers.primitive import String, Integer, Array, Null

#import tornado.wsgi
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options

from pynfe.utils import etree, StringIO, extrair_tag
from pynfe.utils.flags import CODIGOS_ESTADOS

#class ServidorNFEFalso(SimpleWSGISoapApp):
#    @soapmethod(String, Integer, _returns=Array(String))
#    def ping(self, nome, vezes):
#        ret = [nome for i in range(vezes)]
#        return ret

class HandlerStatusServico(tornado.web.RequestHandler):
    sigla_servidor = 'GO'

    def post(self):
        # Obtem o body da request
        xml = self.request.body

        # Transforma em etree
        raiz = etree.parse(StringIO(xml))

        # Extrai a tag do método da request
        tag = extrair_tag(raiz.getroot().getchildren()[0].getchildren()[0])

        # Chama o método respectivo para a tag
        print 'Metodo:', tag
        getattr(self, tag)(raiz)

    def nfeStatusServicoNF2(self, raiz):
        data_hora = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        ret = etree.Element('retConsStatServ')
        etree.SubElement(ret, 'versao').text = '1.00' # FIXME
        etree.SubElement(ret, 'tbAmb').text = '2' # Homologação
        etree.SubElement(ret, 'verAplic').text = self.sigla_servidor
        etree.SubElement(ret, 'cStat').text = '1' # FIXME
        etree.SubElement(ret, 'xMotivo').text = 'Servico em funcionamento normal' # FIXME
        etree.SubElement(ret, 'cUF').text = CODIGOS_ESTADOS[self.sigla_servidor]
        etree.SubElement(ret, 'dhRecbto').text = data_hora
        etree.SubElement(ret, 'tMed').text = '10'
        etree.SubElement(ret, 'dhRetorno').text = data_hora
        etree.SubElement(ret, 'xObs').text = 'Nenhuma informacao adicional'

        xml = etree.tostring(ret, encoding='utf-8', xml_declaration=True)
        self.write(xml)

    def nfeInutilizacaoNF(self, raiz):
        data_hora = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        ret = etree.Element('retInutNFe')
        etree.SubElement(ret, 'versao').text = '1.00' # FIXME

        xml_dados = raiz.getroot().getchildren()[0].getchildren()[0].getchildren()[1].text

        xml = etree.tostring(ret, encoding='utf-8', xml_declaration=True)
        self.write(xml)

if __name__ == '__main__':
    porta = 8080

    # Codigo específico da soaplib
    #application = ServidorNFEFalso()
    #container = tornado.wsgi.WSGIContainer(application)
    #http_server = tornado.httpserver.HTTPServer(container)
    
    tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r'^/nfeweb/services/nfestatusservico.asmx$', HandlerStatusServico), # Consulta de status do serviço
        ])

    ssl_options = {
            'certfile': os.path.join(CUR_DIR, 'tests', 'certificado.pem'),
            'keyfile': os.path.join(CUR_DIR, 'tests', 'key.pem'),
            }

    http_server = tornado.httpserver.HTTPServer(application, ssl_options=ssl_options)
    http_server.listen(porta)
    tornado.ioloop.IOLoop.instance().start()


########NEW FILE########
__FILENAME__ = run_tests
import sys, doctest, os, glob
from getopt import gnu_getopt as getopt

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CUR_DIR)

if __name__ == '__main__':
    run_level = None
    optlist, args = getopt(sys.argv[1:], "l:", ['--level='])
    
    for opt, arg in optlist:
        if opt in ("-l", "--list"):
            run_level = arg.zfill(2)
    
    # Test each package
    if run_level is None:
        search_path = '%s/*.txt' % os.path.join(CUR_DIR, 'tests')
    else: search_path = '%s/%s-*.txt' % \
        (os.path.join(CUR_DIR, 'tests'), run_level)
    
    test_files = glob.glob(search_path)
    test_files = map(lambda i: i[len(CUR_DIR)+1:], test_files)

    # Run the tests
    for fname in test_files:
        print 'Running "%s"...'%(os.path.splitext(os.path.split(fname)[-1])[0])
        doctest.testfile(fname)

    print 'Finished!'


########NEW FILE########
