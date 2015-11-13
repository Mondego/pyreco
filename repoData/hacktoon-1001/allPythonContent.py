__FILENAME__ = Astar
# -*- coding: utf-8 -*-

"""
Algoritmo A* 
Autores: 
    Peter Hart, Nils Nilsson and Bertram Raphael 
Colaborador:
 	Péricles Lopes Machado [gogo40] (pericles.raskolnikoff.gmail.com)
Tipo: 
    graphs
Descrição: 
    O Algoritmo A* é uma generalização do algoritmo de Dijkstra que
permite acelerar a busca com uma heuristica que utiliza propriedades do grafo 
para estimar a distância para o destino. Este algoritmo é ideal quando aplicados
em grades ou representações espaciais e em situações em que já conhecemos a
posição do destino.

Complexidade: 
    O(|E| log |V|)
Dificuldade: 
    medio
Referências:
    [1] http://en.wikipedia.org/wiki/A*_search_algorithm
    [2] http://falapericles.blogspot.com.br/2009/05/o-algoritmo.html
"""

"""
Função para imprimir o caminho
"""
def imprime_caminho(pi, u):
	ux = u[0];
	uy = u[1];

	if pi[ux][uy] == None:
		print u;
	else:
		imprime_caminho(pi, pi[ux][uy]);
		print u;

"""
Função para 'renderizar' o jogador numa posição da grade
"""
def renderizar_grade(G, ux, uy):
	l = list(G[ux]);
	l[uy] = 'x';
	G[ux] = "".join(l);

	for i in range(0, len(G)):
		print " ", G[i];

	print "---------";

	l = list(G[ux]);
	l[uy] = '.';
	G[ux] = "".join(l);

"""
Função para 'renderizar' a trajetória percorrida
"""
def renderizar_caminho(pi, G, u):
	ux = u[0];
	uy = u[1];

	if pi[ux][uy] == None:
		renderizar_grade(G, ux, uy);
	else:
		renderizar_caminho(pi, G, pi[ux][uy]);
		renderizar_grade(G, ux, uy);

from heapq import *;
from math import *;


"""
Este algoritmo utiliza uma grade para realizar a busca.
A origem é marcada com o símbolo 'x' e o destino é marcado
com o simbolo '+'.

"""
G = [
"###..####################..####################..####################..####################..#################.",
".........*........#.#..........*........#.#...........*........#.#...........*........#.............*.......#..",
"....#....#.##.#####.#......#....#.##.#####.#......#....#.##.#####.#......#....#.##.#####........#....#.##.###..",
"#...#....#..#......*..#...#....#..#......*..#...#....#..#......*..#...#....#..#......*......#....#..#......*...",
"#.####...#*##+.....*.##.####...#*##......*.##.####...#*##......*.##.####...#*##......*.##.####...#*##......*.#.",
"#....#..##.........#.##....#..##.........#.##....#..##.........#.##....#..##.........#.##..................#.#.",
"#....#...#.###.##..####....#...#.###.##..####....#...#.###.##..####....#...#.###.##..####........#.###.##..###.",
"#....#.......#..#....##....#.......#..#....##....#.......#..#....##....#...............##............#..#....#.",
"#....#.......#..#....##....#.......#..#....##....#.......#..#....##....#.............................#..#....#.",
"###..#.##########.#######..#.##########.#######..#.##########.#######..#.##########.##.####..#.##########.####.",
"#...##.....#....#.#.......##.....#....#.#..##...##.....#....#.#.......##.....#....#.#.......##.....#....#.#..#.",
"#..........#.....................#.........##..........#.....................#.........##..........#.........#.",
"###..#.....##############..#.....##############..#.x...##############..#.....#########.####..#.....######..###.",
".........*.....................*......................*........#.#...........*..........#...........*.......#..",
"....#....#.##.#####.#......#....#.##.#####.#......#....#.##.#####.#......#....#.##.#####.#......#....#.##..##..",
"#...#....#..#......*..#...#....#..#......*..#...#....#..#......*...........#..#......*..#...#....#..#......*...",
"#.####...#*##......*.##.####...#*##......*.##.####...#*##......*.##.####...#*##......*.##.####...#*##......*.#.",
"#....#..##.........#.##....#..##.........#.##....#..##.........#.##....#..##.........#.......#..##.........#.#.",
"#....#...#.###.##..####....#...#.###.##..####....#...#.###.##..####....#...#.###.##..####....#...#.###.##..###.",
"#....#.......#..#....##....#.......#..#....##....#.......#..#....##....#.......#..#....##............#..#....#.",
"#....#.......#..#....##....#.......#..#....##....#.......#..#....##....#.......#..#....##....#.......#..#....#.",
"###..#.##########.#######..#.##########.#######..#.##########.#######..#.##########.#######..#.##########.####.",
"#...##.....#....#.#..##...##.....#....#.#..##...##.....#....#.#..##...##.....#....#.#..##...##.....#....#.#..#.",
"#..........#.........##..........#.........##..........#.........##..........#.........##..........#.........#.",
"###..#.....##############..#.....##############..#.....##############..#.....##############..#.....###########.",
"..............................................................................................................."];

"""
Localizando a posição do jogador ('x') e do destino ('+')
e inicializa matriz com estimativa de distância D.
"""

D = [];
pi = [];
for x in range(0, len(G)):
	D += [[]];
	pi += [[]];
	for y in range(0, len(G[x])):
		D[x] += [None];
		pi[x] += [None];
		if G[x][y] == 'x':
			s = (x, y);
			l = list(G[x]);
			l[y] = '.';
			G[x] = "".join(l);
		elif G[x][y] == '+':
			t = (x, y);

"""
Possibilidades de movimentação:
...
.x.
...
"""

dx = [-1, -1, -1,  0,  0,  1,  1,  1];
dy = [-1,  0,  1, -1,  1, -1,  0,  1];


"""
Heurística que estima a distancia para o destino:

H(p, t) = sqrt((p.x - t.x)^2 + (p.y - t.y)^2)

Nesse código utilizamos o quadrado da distância euclidiana como estimativa.
"""

def H(s, t):
	Dx = s[0] - t[0];
	Dy = s[1] - t[1];
	return sqrt(Dx * Dx + Dy * Dy);

def dist(s, t):
	Dx = s[0] - t[0];
	Dy = s[1] - t[1];
	return sqrt(Dx * Dx + Dy * Dy);



Q = [];

D[s[0]][s[1]] = 0;
heappush(Q, (0, s));

"""
Enquanto a fila de prioridade não estiver vazia tente verificar se o topo
da fila é melhor opção de rota para se chegar nos adjascentes. Como o topo
já é o mínimo, então garante-se que D[u] já está minimizado no momento.
"""
while Q:
	p = heappop(Q)[1];

	u = (p[0], p[1]);
	ux = u[0];
	uy = u[1];

	"""
	Como já chegamos no destino, podemos parar a busca
	"""
	if u == t:
		break;

	for i in range(0, len(dx)):
		vx = u[0] + dx[i];
		vy = u[1] + dy[i];

		v = (vx, vy);

		duv = dist(u, v);
		if vx > -1 and vx < len(G):
			if vy > -1 and vy < len(G[vx]): 
				if (D[vx][vy] > D[ux][uy] + duv or D[vx][vy] == None) and G[vx][vy] != '#':
					D[vx][vy] = D[ux][uy] + duv;
					pi[vx][vy] = u;
					"""
					A única diferença entre o A* e o dijkstra é o modo como é ordenado a heap.
					No caso, ela utiliza a heurítica H que procura colocar no topo os pontos mais
					próximos do destino.
					"""
					heappush(Q, (D[vx][vy] + H(v, t), v));
		

if D[t[0]][t[1]] != None:
	print "A distância entre s e t é: ", D[t[0]][t[1]]; 
	"""
	Descomente essa linha caso queira ver a sequencia de passos percorrido pelo jogador
	"""
	imprime_caminho(pi, t);
	"""
	Descomente essa linha se quiseres ver o caminho percorrido na grade
	"""
	#renderizar_caminho(pi, G, u);
else:
	print "Não existe caminho entre s e t!"


########NEW FILE########
__FILENAME__ = hamming
# coding: utf-8
'''
Hamming Distance
Autor:
	Hamming
Colaborador:
	Adriano Melo <adriano@adrianomelo.com>
	Dayvid Victor <victor.dvro@gmail.com>
Tipo:
	artificial-intelligence
Descrição:
	Algorítmo para calcular a distância entre vetores com dados categóricos.
Complexidade:  
	O(n) - sendo n o tamanho do vetor
Dificuldade:
	fácil
Referências:

'''

def hamming(a, b):
	return sum([hamming_i(ai, bi) for ai, bi in zip(a,b)])

def hamming_i(ai, bi):
	return (0 if ai == bi else 1)

def knn(k, treino, padrao, distancia=lambda a,b: sum([(c-d)**2 for c,d in zip(a,b)])):
	k_nearest = sorted([[distancia(pe[:-1], padrao), pe[-1]] for pe in treino])[:k]
	return max(set([e[-1] for e in k_nearest]), key = [e[-1] for e in k_nearest].count)



if __name__ == '__main__':
	train = [['gordo', 'baixo', 'devagar', 'golfista'],
		['magro', 'alto', 'rapido', 'jogador de basquete'],
		['magro', 'baixo','rapido', 'jogador de futebol'],
		['gordo', 'alto', 'rapido', 'jogador de futebol americano'],
		['medio', 'medio', 'rapido', 'jogador de tenis']]
	
	padrao = ['magro', 'medio', 'rapido']
	
	print knn(1, train, padrao, distancia = hamming)


########NEW FILE########
__FILENAME__ = knn
# coding: utf-8
'''
K-Nearest Neighboor (k-NN)
Autor:
    Belur V. Dasarathy
Colaborador:
	Adriano Melo <adriano@adrianomelo.com>
	Dayvid Victor <victor.dvro@gmail.com>
Tipo:
    artificial-intelligence
Descrição:
    Algoritmo de aprendizagem baseado em instâncias.
    Uma matriz é dada ao algoritmo contendo vetores e as classes que eles pertencem,
    um vetor não classificado é a segunda entrada do algoritmo. 
    A saída é a classe que o vetor não classificado pertence.
Complexidade:  
    O(n * m * k) = O(n)
    n: número de instâncias
    m: tamanho dos vetores
    k: K-primeiros vizinhos
Dificuldade:
    medio
Referências:
    Belur V. Dasarathy, ed (1991). Nearest Neighbor (NN) Norms: NN Pattern Classification Techniques. ISBN 0-8186-8930-7.
'''

def knn(k, treino, padrao, distancia=lambda a,b: sum([(c-d)**2 for c,d in zip(a,b)])):
	k_nearest = sorted([[distancia(pe[:-1], padrao), pe[-1]] for pe in treino])[:k]
	return max(set([e[-1] for e in k_nearest]), key = [e[-1] for e in k_nearest].count)

treino = [
	[1,2,3,4,5,6,'classe 1'],
        [1,2,3,3,5,6,'classe 1'],
        [2,3,5,6,7,8,'classe 2'],
        [9,9,9,9,9,9,'classe 3'],
        [9,9,9,9,9,8,'classe 3'],
        [9,9,9,9,9,7,'classe 3']]

print knn(1, treino, [2,3,4,6,7,8])
print knn(3, treino, [2,3,4,6,7,8])
print knn(6, treino, [2,3,4,6,7,8])


########NEW FILE########
__FILENAME__ = rgb-to-cmyk
# encoding: utf-8

'''
RGB to CMYK
Autor:
    ?
Colaborador:
    Aurélio A. Heckert
Tipo:
    color
Descrição:
    Converte uma cor definida em RGB para CMYK.

    RGB é um sistema aditivo de definição de cores, representa a mistura de luz. Suas componentes são (em ordem) vermelho, verde e azul.
    CMYK é um sistema subtrativo de definição de cores, representa a mistura de pigmentos. Suas componentes são (em ordem) ciano, magenta, amarelo e preto. O preto no CMYK deriva uma necessidade do uso prático, já que a mistura dos 3 pigmentos é custoso, não é realmente preto e a sobreposição de impressões tornaria o desalinhamento mais perceptível nos detalhes escuros.
    O algorítimo deste exemplo considera as componentes como valores flutuantes entre 0 e 1, onde 0 significa sem representação e 1 máxima representação. Sendo assim o branco seria (1,1,1) em RGB e (0,0,0,0) em CMYK, o vermelho intenso seria (1,0,0) em RGB e (0,1,1,0) em CMYK e o laranja seria (1,0.5,0) em RGB e (0,0.5,1,0) em CMYK. A representação das componentes em valores flutuantes entre 0 e 1 pode parecer estranho pelo nosso costume em ver cores definidas com 1 byte por unidade, mas essa representação é bastante útil em vários algorítimos para manipulação de cores e ainda viabiliza representações com maior profundidades de cores (mais de 1 byte por componente).
Complexidade:  
    O(1)
DIficuldade:
    facil
Referências:
    http://en.wikipedia.org/wiki/RGB
    http://en.wikipedia.org/wiki/CMYK
'''

def rgb2cmyk( red, green, blue ):

    black = min( 1-red, 1-green, 1-blue )
    nb = 1 - black  # negative black
    if black == 1:
        cyan    = 0
        magenta = 0
        yellow  = 0
    elif nb > 0:
        cyan    = ( nb - red   ) / nb
        magenta = ( nb - green ) / nb
        yellow  = ( nb - blue  ) / nb
    else:
        cyan    = 1 - red
        magenta = 1 - green
        yellow  = 1 - blue

    return "%.1f  %.1f  %.1f  %.1f" % ( cyan, magenta, yellow, black )


print 'Preto:\t\t\t',       rgb2cmyk( 0.0, 0.0, 0.0 )
print 'Cinza escuro:\t\t',  rgb2cmyk( 0.3, 0.3, 0.3 )
print 'Cinza médio:\t\t',   rgb2cmyk( 0.5, 0.5, 0.5 )
print 'Cinza claro:\t\t',   rgb2cmyk( 0.7, 0.7, 0.7 )
print 'Branco:\t\t\t',      rgb2cmyk( 1.0, 1.0, 1.0 )
print 'Vermelho vivo:\t\t', rgb2cmyk( 1.0, 0.0, 0.0 )
print 'Vermelho sangue:\t', rgb2cmyk( 0.7, 0.0, 0.0 )
print 'Laranja:\t\t',       rgb2cmyk( 1.0, 0.5, 0.0 )
print 'Verde Musgo:\t\t',   rgb2cmyk( 0.6, 0.7, 0.6 )

########NEW FILE########
__FILENAME__ = derangement
#!usr/bin/python
# encoding: utf-8

"""
Desarranjo
Autor:
    Pierre Raymond de Montmort
Colaborador:
    Carlos Rodrigues c11a10r9l8o7s6f5e4l3i2x1@yahoo.com.br
Tipo:
    math
Descrição:
    Algoritmo que calcula permutação caótica
Dificuldade:
    facil
Complexidade:
    ?
Referência:
    http://pt.wikipedia.org/wiki/Desarranjo
"""

from __future__ import division

def fatorial(x):
    if x <= 1:
        return 1
    else:
        return x * fatorial(x-1)

n = 5
d = 0
for i in range(0, n):
    d = d + ((-1) ** i / fatorial(i))
print fatorial(n) * d

########NEW FILE########
__FILENAME__ = cesar
#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
Cesar Cipher (Cifra de César)
Autor:
    César
Colaborador:
    Apu, Sigano, InFog, Paulo, Doug, ExHora <gccsd@lista.gccsd.com.br>
Tipo:
    crypto
Descrição:
    Este algoritmo implementa a Cifra de César
    Este algoritmo foi implementado em um Dojo do Grupo de Compartilhamento do
    Conhecimento Santos Dumont <http://gccsd.com.br>
Complexidade:  
    ?
Dificuldade:
    facil
Referências:
    http://pt.wikipedia.org/wiki/Cifra_de_C%C3%A9sar
Licenca:
    GPL
"""

__authors__ = (
    "Apu",
    "Sigano",
    "InFog",
    "Paulo",
    "Doug",
    "ExHora"
)

import string

class Cesar(object): 
    
    def __init__(self):
        self.INICIO = 65
        self.FIM = 90
        self.ESPACO = 32
    
    def crypt(self, entrada = "", chave = 0):
        saida = ""
        entrada = entrada.upper()

        for letra in entrada:
            valor = ord(letra)
            
            if (not valor == self.ESPACO):
                valor += chave
                if (valor > self.FIM):
                    valor -= 26
            saida += chr(valor)
            
        return saida
    
    def decrypt(self, entrada = "", chave = 0):
        saida = ""
        entrada = entrada.upper()
        
        for letra in entrada:
            valor = ord(letra)
            
            if (not valor == self.ESPACO):
                valor -= chave
                if (valor < self.INICIO):
                    valor += 26
            saida += chr(valor)
        
        return saida

c = Cesar()
print c.crypt("a ligeira raposa marrom saltou sobre o cachorro cansado", 3)
print c.decrypt("D OLJHLUD UDSRVD PDUURP VDOWRX VREUH R FDFKRUUR FDQVDGR", 3)

########NEW FILE########
__FILENAME__ = rot13
#!/usr/bin/env python3.1

"""
ROT13
Autor:
    ?
Colaborador:
    Fernando Medeiros <fekomedeiros - at - gmail.com>
Tipo:
    sequence
Descrição: 
    Implementação do algoritmo ROT-13, ou "Rotate By 13".
    É um procedimento simples mas eficaz para garantir que textos eletrônicos 
    não sejam lidos por distração ou acidente.
    Util para proteger mensagens que talvez o leitor não queira ler. 
    Exemplo, "spoilers" sobre determinado assunto em Fóruns ou listas de discussão.
Complexidade:
    ?
Dificuldade:
    facil
Referências:
    http://pt.wikipedia.org/wiki/ROT13
"""

def rot13(text):
    alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    rotated = 'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'
    r13 = "".maketrans(alpha, rotated)
    return text.translate(r13)

#Exemplos de uso:

print(rot13("Agora estou usando ROT-13!"))
#Exibe a mensagem: Ntben rfgbh hfnaqb EBG-13!

print(rot13("Ntben rfgbh hfnaqb EBG-13!"))
#Exibe a mensagem: Agora estou usando ROT-13!
#Note que a mesma função é usada para codificar e decodificar o texto.

########NEW FILE########
__FILENAME__ = rsa
#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
"""
RSA
Autor:
    Ron Rivest, Adi Shamir, e Leonard Adleman 
Colaborador:
    Juan Lopes <me@juanlopes.net>
Tipo:
    crypto
Descri��o: 
    Implementa��o simples do algoritmo RSA.
    
    Este algoritmo se baseia na dificuldade computacional da fatora��o de
    n�meros inteiros.
    
    A id�ia que a chave p�blica e privada sejam baseadas na multiplica��o
    de dois n�meros primos (geralmente grandes) e que a rela��o entre elas
    exija o conhecimento dos fatores dessa multiplica��o.
Complexidade:
    O(n)
Dificuldade:
    medio
Refer�ncias:
    http://en.wikipedia.org/wiki/RSA_(algorithm)
"""

def gcd(a,b):
    if b==0: return (1, 0)
    q = a/b
    x,y = gcd(b, a-q*b)
    return (y, x-q*y)
    
def inverse(a, b):
    x,y = gcd(a,b)
    return (x if x > 0 else x+b)
   
def rsa(n, e, M):
    return map(lambda m: pow(m, e, n), M)
   
p,q = 41, 47              #primos             
n,phi = p*q, (p-1)*(q-1)  #m�dulo and totiente
e,d = 7, inverse(7,phi)   #expoentes p�blico e privado

plain = (1,2,3,4,5,6,7,42)
encrypted = rsa(n, e, plain)
plain_again = rsa(n, d, encrypted)

print 'Chave p�blica:', (n,e)
print 'Chave privada:', (n,d)
print '---'
print 'Mensagem original:', plain
print 'Mensagem encriptada:', encrypted
print 'Mensagem decriptada:', plain_again
########NEW FILE########
__FILENAME__ = vigenere
#!usr/bin/python
# encoding: utf-8

"""
Vigenère cipher (Cifra de Vigenère)
Autor:
  Giovan Battista Bellaso (1553) "La cifra del. Sig. Giovan Battista Bellaso"
  Foi erradamente atribuida a Blaise de Vigenère
Colaborador:
  damor - dave-world (at) hotmail.com
Tipo:
  Crypto
Descrição:
  Este algoritmo implementa o metodo de criptografia "Cifra de Vigenère"
  "A cifra de Vigenère consiste no uso de várias cifras de César em sequência,
  com diferentes valores de deslocamento ditados por uma "palavra-chave"" - Wiki
Complexidade:
  ?
Dificuldade:
  facil
Referências: (opcional)
  http://pt.wikipedia.org/wiki/Cifra_de_Vigen%C3%A8re
Licenca:(opcional)
  GPL
"""

class Vigenere(object):
  def __init__(self):
    self.tabulaRecta = [ [ 0 for i in range(26) ] for j in range(26) ] # Construir a tabula recta (Grelha de Vigenere)
    for i in range(26):
      for j in range(26):
        ch = ord("A")+j+i
        if (ch>90): ch-=26
        self.tabulaRecta[i][j] = chr(ch)

  def crypt(self, plaintext = "", chave= ""):
    self.newKey=chave
    while len(self.newKey)<len(plaintext): self.newKey+=chave
    chave = self.newKey[:len(plaintext)]
    pos = 0
    cipher = ""
    for c in plaintext:
      cipher += self.tabulaRecta[ord(chave[pos]) % 26][ord(c) % 26]
      pos += 1
    return cipher

  def decrypt(self, ciphertext = "", chave=""):
    self.newKey=chave
    while len(self.newKey)<len(ciphertext): self.newKey+=chave
    chave = self.newKey[:len(ciphertext)]
    cipher = ""
    iter = 0
    for c in chave:
      pos = 0
      for k in range(26):
        if (self.tabulaRecta[ord(c)-ord("A")][k] == ciphertext[iter]):
          cipher += chr(ord("A")+pos)
        pos += 1
      iter += 1
    return cipher

v = Vigenere()
encWord = v.crypt("ATACARBASESUL","LIMAO")
print encWord
print v.decrypt(encWord,"LIMAO")

########NEW FILE########
__FILENAME__ = arraysum
# coding: utf-8
'''
Array Sum
Autor:
    ?
Colaborador:
    Dayvid Victor (victor.dvro@gmail.com)
Descricao:
    Esse programa recebe como parametro uma lista
    e retorna a soma dos elementos desta lista.
Complexidade:
    O(n)
Dificuldade:
    facil
Licenca:
    GPL
'''

def arraysum(l, key = lambda a, b: a + b):
	s = 0
	for e in l:
		s = key(s,e)
	return s

if __name__ == '__main__':
	l1 = [1,2,3,4,5,6,7,8,9,10]
	l2 = [-4,-3,-2,-1,0,1,2,3,4]

	print arraysum(l1)
	print arraysum(l2)


########NEW FILE########
__FILENAME__ = heap
# -*- encoding: utf-8 -*-
"""
Binary Heap
Autor:
    M. D. ATKINSON, J. R. SACK, N. SANTORO, and T. STROTHOTT
Colaborador:
    Juan Lopes (me@juanlopes.net)
Tipo:
    data-structures
Descrição:
    Implementação de priority queue usando uma binary min-heap.
    
Complexidade:  
    Inserção: O(log n) 
    Remoção: O(log n)
    Obter mínimo: O(1)
Dificuldade:
    Fácil
Referências: (opcional)
    http://en.wikipedia.org/wiki/Binary_heap
"""

class BinaryHeap:
    def __init__(self, V = []):
        self.V = [None] + list(V)
        self.heapify()
        
    def heapify(self):
        for i in range(self.count()/2, 0, -1):
            self.bubble_down(i)
        
    def count(self):
        return len(self.V) - 1
        
    def top(self):
        return (self.V[1] if self.count() > 0 else None)

    def push(self, value):
        self.V.append(value)
        self.bubble_up(self.count())
    
    def pop(self):
        if self.count() == 0: return None
        
        value = self.V[1]
        self.V[1] = self.V[-1]
        self.V.pop()
        self.bubble_down(1)
        return value
   
    def pop_all(self):
        while self.count() > 0:
            yield self.pop()
   
    def bubble_up(self, n):
        while n != 1 and self.less(n, n/2):
            self.swap(n, n/2)
            n /= 2
            
    def bubble_down(self, n):
        while self.less(n*2, n) or self.less(n*2+1, n):
            c = self.min(n*2, n*2+1)
            self.swap(n, c)
            n = c

    def less(self, a, b):
        if a>self.count(): return False
        if b>self.count(): return True
        return self.V[a]<self.V[b]
        
    def min(self, a, b):
        return (a if self.less(a,b) else b)
        
    def swap(self, a, b):
        self.V[a], self.V[b] = self.V[b], self.V[a]

heap = BinaryHeap()
heap.push(10)
heap.push(2)
heap.push(5)
heap.push(-100)
print heap.pop() #-100
print heap.pop() #2
print heap.pop() #5
print heap.pop() #10

print
print 'Heap sort'

V = [10, 2, 5, -100]
print V, '->', list(BinaryHeap(V).pop_all())

########NEW FILE########
__FILENAME__ = leap-year
# -*- encoding: utf-8 -*-
"""
Bissexto
Autor:
    ?
Colaborador:
    Bruno Lara Tavares <bruno.exz . at . gmail . com>
Tipo:
    date
Descrição:
    Calcula os próximos anos bissextos
Complexidade:
    ?
Dificuldade:
    facil
Referências:
    http://pt.wikipedia.org/wiki/Ano_bissexto#Calend.C3.A1rio_Gregoriano

"""

from datetime import datetime

def anoBissexto(anos):
	anoAtual = datetime.now().year
	proximoAno = anoAtual + anos
	for ano in range(anoAtual,proximoAno):
		if ano % 4 == 0 and (ano % 100 or ano % 400 == 0):
			yield ano

for ano in anoBissexto(100): print ano

########NEW FILE########
__FILENAME__ = financiamento
# -*- encoding: utf-8 -*-

"""
Financiamento
Autor:
    ?
Colaborador:
    Bruno Lara Tavares <bruno.exz@gmail.com>
Tipo:
    ?
Descrição:
	Calcula o valor das parcelas do financiamneto
	baseado no capital inicial e taxa de juros
	de acordo na função Price
Complexidade:
    ?
Dificuldade:
    facil
Referências:
    http://pt.wikipedia.org/wiki/Tabela_price#C.C3.A1lculo
"""

def parcelas(investimento, juros, periodo):
	return (investimento*juros) / (1 - (1/(1+juros)**periodo))
	
print parcelas(1000, 0.03, 4)

########NEW FILE########
__FILENAME__ = haversine
# -*- encoding: utf-8 -*-
"""
Haversine
Autor:
    ?
Colaborador:
    Bruno Lara Tavares <bruno.exz . at . gmail . com>
Tipo:
    geography
Descrição:
    Calcula a distancia mais curta
    entre dois pontos com latitude e longitude
    na superficie da Terra
    usando a formula de haversine
Complexidade:
    ?
Dificuldade:
    medio
Referências:
    http://en.wikipedia.org/wiki/Haversine_formula

"""
from __future__ import division
import math


def strTodegree(string):
    grau, minuto, segundo = [int(x) for x in string.split()]
    if(string.find("-") == -1):
        grau += (minuto/60) + (segundo/3600)
    else:
        grau -= (minuto/60) + (segundo/3600)
    return grau


def haversin(theta):
	return math.sin(theta/2)**2


def distancia(latitude1, longitude1, latitude2, longitude2):
	Radius = 6371 #Terra
	deltaLatitude = math.radians(latitude2 - latitude1)
	deltaLongitude = math.radians(longitude2 - longitude1)
	h = haversin(deltaLatitude) + math.cos(math.radians(latitude1))*math.cos(math.radians(latitude2))*haversin(deltaLongitude)
	return 2*Radius*math.asin(math.sqrt(h))

print distancia(strTodegree("53 08 50"),strTodegree("-01 50 58"),strTodegree("52 12 16"),strTodegree("00 08 26"))

########NEW FILE########
__FILENAME__ = BellmanFord
# -*- coding: utf-8 -*-

"""
Algoritmo de Bellman-Ford.

Autor:
	Richard Bellman & Lester R. Ford Jr. (1958)

Colaborador:
	Pedro Arthur Duarte (JEdi)
	pedroarthur.jedi@gmail.com

Tipo:
	graph
	shortest path on directed graphs with negative weighted edges

Descrição:
	O algoritmo de Bellman-Ford determina o caminho mais curto de origem única
	em grafos com arestas de pesos negativos. Para grafos sem arestas negativas,
	o algoritmo de Dijkstra apresenta melhor desempenho.

Complexidade:
	O(V*E), onde 'V' é a cardinalidade o conjunto de vértices e 'E' a
	cardinalidade do conjunto de arestas.

Dificuldade:
	media

Referências:
	http://en.wikipedia.org/wiki/Bellman-Ford_algorithm

Licença:
	GPLv3

"""

from sys import maxint

class NegativeWeightCycleError(Exception):
	pass


class Vertex:
	'''
	Abstração de vértice para a implementação através de lista de adjacência;
	estão inclusos atributos extras para a implementação do algoritmo
	'''
	def __init__(self, label, distance, predecessors=None):
		self.label = label

		self.distance = distance
		self.predescessor = None

	def __repr__(self):
		return str(self.label)

class Edge:
	'''
	Abstração de aresta para a implementação através de lista de adjacência
	'''
	def __init__(self, source, destination, weight):
		self.src = source
		self.dst = destination
		self.wht = weight

class Graph:
	'''
	Abstração de grafo para a implementação através de lista de adjacência.
	'''
	def __init__(self, graph=None):
		'''
		Caso seja passada uma matriz de adjacência, essa é transformada numa
		lista de adjacência.
		'''
		self.vertex = { }
		self.edges = [ ]

		if graph == None:
			return

		for i in xrange(0, len(graph)):
			for j in xrange(0, len(graph)):
				if graph[i][j] == None:
					continue

				self.addEdge(i, j, graph[i][j])

	def addEdge(self, source, destination, weight):
		if source not in self.vertex:
			self.vertex[source] = Vertex(source, maxint)

		if destination not in self.vertex:
			self.vertex[destination] = Vertex(destination, maxint)

		self.edges.append(
			Edge(self.vertex[source], self.vertex[destination], weight))

class BellmanFord:
	def __init__(self, g):
		self.graph = g

	def adjacencyMatrixShortestPath(self, source, destination):
		'''Implementação através de matriz de adjacência'''

		# Etapa de inicialização: todas as distâncias são definidas como
		# infinitas para que sejam então atualizadas durante a relaxação
		self.distances = [ maxint for s in self.graph ]
		self.distances[source] = 0

		# Arranjo auxiliar para que possamos reconstruir o menor caminho
		self.predecessors = [ 0 for s in self.graph ]

		# Para cada v em V:
		for i in xrange(0, len(self.graph)):
			# Para cada e em E
			#	Aqui, devido ao uso da matriz de adjacência, precisamos
			#	utilizar dois laços "para" (for) de forma que possamos
			#	percorrer todas as aresta
			for u in xrange(0, len(self.graph)):
				for v in xrange(0, len(self.graph)):
					if self.graph[u][v] == None:
						continue

					# Etapa de "relaxação" do grafo
					if self.distances[u] + self.graph[u][v] < self.distances[v]:
						self.distances[v] = self.distances[u] + self.graph[u][v]
						self.predecessors[v] = u

		# Verificação da existência de círculos negativos
		for u in xrange(0, len(self.graph)):
			for v in xrange(0, len(self.graph)):
				if self.graph[u][v] == None:
					continue

				if self.distances[u] + self.graph[u][v] < self.distances[v]:
					raise NegativeWeightCycleError

		# lista de saída; índice -1 indica o custo total do menor caminho
		output = [ self.distances[destination] ]

		# Reconstruindo o menor caminho através do predecessor do destino
		while True:
			output.insert(0, destination)

			if destination == source:
				break
			else:
				destination = self.predecessors[destination]

		# Crianças, não façam isso em casa.
		return output[:-1], output[-1]

	def adjacencytListShortestPath(self, source, destination):
		'''
		Implementação através de lista de adjacência;

		Funcionalmente, o mesmo código acima. Porém, bem mais limpo e menos
		devorador de memória. Adequado para matrizes esparsas.
		'''
		
		source, destination = (self.graph.vertex[source],
								self.graph.vertex[destination])

		# A etapa de inicialização está parcialmente implícita no construtor
		# da classe Vertex. Assim, precisamos apenas atualizar o valor de
		# distância do nó origem.
		source.distance = 0

		for _ in self.graph.vertex:
			for e in self.graph.edges:
				if e.src.distance + e.wht < e.dst.distance:
					e.dst.distance = e.src.distance + e.wht
					e.dst.predescessor = e.src

		for e in self.graph.edges:
			if e.src.distance + e.wht < e.dst.distance:
				raise NegativeWeightCycleError

		output = [ destination.distance ]

		while True:
			output.insert(0, destination)

			if destination == source:
				break
			else:
				destination = destination.predescessor

		return output[:-1], output[-1]

'''
Matriz de adjacência; None pode ser utilizado para representar a inexistência
de arestas entre dois vértices.
'''
graph = [
	[7, 6, 8, 3, 5, 3, 2, 7, 1, 2, ],
	[0, 5, 2, 9, 1, 6, 2, 9, 9, 7, ],
	[6, 8, 7, 5, 8, 5, 7, 9, 8, 2, ],
	[6, 9, 7, 5, 8, 9, 8, 6, 3, 4, ],
	[0, 4, 8, 1, 6, 5, 8, 0, 7, 9, ],
	[2, 3, 3, 9, 9, 0, 0, 3, 0, 4, ],
	[7, 8, 0, 7, 7, 2, 9, 6, 0, 8, ],
	[3, 3, 5, 4, 8, 8, 8, 4, 4, 0, ],
	[9, 7, 2, 5, 0, 5, 4, 9, 0, 3, ],
	[6, 1, 8, 6, 6, 6, 1, 6, 7, 9, ],
]

# Calculando o menor caminho através da matriz
print BellmanFord(graph).adjacencyMatrixShortestPath(0,9)

# Calculando o menor caminho através da lista
print BellmanFord(Graph(graph)).adjacencytListShortestPath(0,9)

########NEW FILE########
__FILENAME__ = Dijkstra
# -*- coding: utf-8 -*-

"""
Algoritmo de Dijkstra (com lista de adjascencias)
Autores: 
    Edsger Dijkstra
Colaborador:
 	Péricles Lopes Machado (pericles.raskolnikoff@gmail.com)
Tipo: 
    graphs
Descrição: 
    O Algoritmo de Dijsktra é um algoritmo em grafos clássico que determina a
    menor distância de um determinado vértice para todos os outros. Nessa implementação
	utiliza-se uma heap
Complexidade: 
    O(|E| log |V|)
Dificuldade: 
    medio
Referências:
    [1] http://en.wikipedia.org/wiki/Dijkstra%27s_algorithm
    [2] Cormem, Thomas H. Introduction to Algorithms, 3rd Edition. 
        ISBN 978-0-262-53305-8. Páginas 658-659.
"""

from heapq import *;

"""
Função para imprimir rota
"""

def imprime_rota(pi, u):
	if pi[u] != None:
		imprime_rota(pi, pi[u]);
	print " ", u;

"""
Lista de adjacência; Para cada nó 'u' é fornecida uma lista de pares (v, d), onde 'v' é um 
nó que está conectado a 'u' e 'd' é a distancia entre 'u' e 'v'
"""

G = [
	[(1, 2), (3, 4), (5, 3), (8, 9)], 
	[(2, 7), (4, 6), (7, 8)],
	[(4, 9), (7, 9)],
	[(1, 13), (4, 4), (6, 3), (2, 3)], 
	[(1, 23), (7, 4), (5, 3), (8, 1), (4, 9)], 
	[(3, 11), (4, 7), (8, 9)], 
	[(5, 2), (3, 5), (4, 3), (5, 9)], 
	[(1, 2), (7, 4), (5, 9), (6, 8)], 
	[(7, 2), (2, 3), (1, 1), (3, 1)], 
]; 


"""
Origem s e destino t
"""
s = 1;
t = 6;

N = len(G);

"""
Estimativa de distancia inicial
None representa o infinito e código pai usado para recuperar a rota
"""
D = [];
pi = [];

for i in range(0, N):
	D += [None];
	pi += [None];

"""
Priority queue utilizada para o acesso rápido a melhor estimativa
"""
Q = [];

D[s] = 0;
heappush(Q, (0, s));

"""
Enquanto a fila de prioridade não estiver vazia tente verificar se o topo
da fila é melhor opção de rota para se chegar nos adjascentes. Como o topo
já é o mínimo, então garante-se que D[u] já está minimizado no momento.
"""
while Q:
	u = heappop(Q)[1];
	for adj in G[u]:
		v = adj[0];
		duv = adj[1];
		if D[v] > D[u] + duv or D[v] == None:
			D[v] = D[u] + duv;
			pi[v] = u;
			heappush(Q, (D[v], v));

if D[t] != None:
	print "Distância(", s, ",", t, ") = ", D[t]; 
	print "Rota:";
	imprime_rota(pi, t);
else:
	print "Não há rota entre os nós ", s, " e ", t;



########NEW FILE########
__FILENAME__ = EdmondsKarp
# -*- coding: utf-8 -*-

"""
Algoritmo de Edmonds-Karp.

Autor:
  Jack Edmonds & Richard Karp (1972)

Colaborador:
  Pedro Arthur Duarte (JEdi)
  pedroarthur.jedi@gmail.com

Tipo:
  graph

Descrição:
  O Algoritmo de Edmonds-Karp é uma implementação do método de Ford-Fulkerson
  para o cálculo do fluxo máximo em uma rede de fluxos. Esse algoritmo é
  idêntico ao método de Ford-Fulkerson excetuando-se no critério que utiliza
  para a escolha do caminho aumentante: o caminho precisa ser o menor caminho
  que possibilita o aumento do fluxo.

Complexidade:
  O(V*E²),  onde 'V' é a cardinalidade o conjunto de vértices e 'E' a
            cardinalidade do conjunto de arestas.

Dificuldade:
  alta (?)

Referências:
  http://en.wikipedia.org/wiki/Edmonds

Licença:
  GPLv3

"""

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
from sys import stdin;

DIMACS = 0
WFLOW = 1
RAW = 2

IMPERATIVE = 0
FUNCTIONAL = 1

class EdmondsKarp:
  # Cria nova instância da classe.
  # Parâmetros:
  #   c: matriz de fluxos (f[i,j] = c[i][j])
  #   s: vértice do qual se origina o fluxo;
  #   t: vértice de destino do fluxo;
  def __init__(self, c, s, t):
    self.c = c
    self.s = s
    self.t = t

    # Matriz auxiliar dos fluxos
    self.f = [[0] * len(i) for i in c]

    #print c

  # Iterador para auxiliar na construção da resposta
  def __iter__(self):
    return self

  # Busca primeiro em largura:
  def next(self):
    q = [ self.s ]
    p = { self.s: [] }

    # Critério: capacidade(e) - fluxoatual(e) > 0

    # Implementação imperativa (aquela que se encontra geralmente nos livros)
    if self.approach == IMPERATIVE:
      for u in q:
        for v in xrange(len(self.c)):
          if self.c[u][v] - self.f[u][v] > 0 and v not in p:
            p[v] = p[u] + [(u,v)]
            if v == self.t:
              return p[v]
            q.append(v)

    # Implementação por meio de diretivas funcionais. Bonito, mas impraticável
    # para grandes instâncias desse problema.
    else:
      fcond = (lambda x: x[0][1] - x[1] > 0 and x[0][0] not in p)
      for u in q:
        for v in map(
                  lambda x: x[0][0],
                  filter(fcond, zip(enumerate(self.c[u]), self.f[u]))):
          p[v] = p[u] + [(u,v)]
          if v == self.t:
            return p[v]
          q.append(v)

    raise StopIteration

  # Esse algoritmo também é capaz de determinar o corte mínimo.
  # Esse método faz isso :-)
  def MinCutVertex(self):
    q = [ self.s ]
    o = [ ]

    for u in q:
      for v in xrange(len(self.c)):
        if self.c[u][v] - self.f[u][v] > 0 and v not in o:
          o.append(v)
          q.append(v)

    return o

  # Retorna a matriz de fluxos
  def FlowEdges(self, outtype=RAW):
    # Retorna a própria matriz de fluxos
    if outtype == RAW:
      return self

    # seleciona apenas os vértices que possuem algum fluxo
    if outtype == WFLOW:
      q = [ self.s ]
      p = []
      u = 0

      fcond =

      for u in q:
        f = map(
              lambda x: x[0][0],
              filter(
                   lambda x:x[1]>0 and (u,x[0][0],self.f[u][x[0][0]]) not in p,
                   zip(enumerate(self.c[u]), self.f[u])
              )
        )
        for v in f:
          p = p + [(u,v,self.f[u][v])]
          q.append(v)

      return p

    # retorna nada =p
    else:
      return [ ]

  # Implementação do algoritmo de Edmonds-Karp
  def MaxFlow(self, approach=IMPERATIVE):
    self.approach = approach

    # Enquanto houverem caminhos aumentantes,
    # selecione aquele de menor custo;
    for p in self:

      # Dentro desse caminho, encontre a aresta
      # que possuí menor capacidade de vazão:
      mf = min(map(lambda e: self.c[e[0]][e[1]] - self.f[e[0]][e[1]], p))

      # Ajuste os valores da matriz de fluxo de
      # acordo com o vazão da aresta encontrada
      # no passo anterior
      for u,v in p:
        self.f[u][v] += mf
        self.f[v][u] -= mf

    # Retorna o fluxo máximo
    return sum(self.f[self.s])


########NEW FILE########
__FILENAME__ = FloydWarshall
 
# -*- coding: utf-8 -*-

"""
Algoritmo de Floyd-Warshall.

Autor:
	Robert W. Floyd & Stephen Warshall (1962)

Colaborador:
	Pedro Arthur Duarte (JEdi)
	pedroarthur.jedi@gmail.com

Tipo:
	graph
	all-pairs shortest path in weighted graphs
	dynamic programming

Descrição:
	O algoritmo de Floyd-Warshall computa os caminhos mais curtos entre todos os pares de um grafo valorado de pesos arbitrários.

	A formulação em programação dinâmica para esse problema consiste em
	determinar de forma bottom-up os menores caminhos para todos os vértices
	considerando que os caminhos intermediários consistem apenas de um
	subconjunto de vértices. Assim, $d_{ij}^{(k)}$ é menor caminho do vértice
	$i$ ao vértice $j$ tal que esse caminho consiste apenas de vértices
	intermediários em $k$. Assim, a seguinte formulação é empregada no
	algoritmo de Floyd-Warshall:

	$$ d_{ij}^{(k)} = min(d_{ij}^{(k)}, d_{ik}^{(k-1)} + d_{kj}^{(k-1)}) $$

	Essa formulação assuma que $d_{ij} = 0$ se $i=j$, e $d_{ij}=\infty$ se não
	há uma aresta entre os vértices $i$ e $j$.

Complexidade:
	Θ(V³),  onde 'V' é a cardinalidade o conjunto de vértices.

Dificuldade:
	média

Referências:
	Cormen; Leiserson; Rivest; Stein. Introduction to Algorithms (2 ed). ISBN: 978-0262033848.
	https://secure.wikimedia.org/wikipedia/en/wiki/Floyd–Warshall_algorithm

Licença:
  GPLv3

"""

from sys import maxint as Infinity

class NoSuchAPathError(Exception):
	pass

class FloydWarshall:
	def __init__(self, matrix):
		self.matrix = [ ]
		self.paths = [ ]

		for r in matrix:
			self.matrix.append([ ])
			self.paths.append([ ])

			for c in r:
				self.matrix[-1].append(c)
				self.paths[-1].append(None)

	def shortestPaths(self):
		for k in xrange(0, len(self.matrix)):
			for i in xrange(0, len(self.matrix)):
				for j in xrange(0, len(self.matrix)):
					if self.matrix[i][k] + self.matrix[k][j] < self.matrix[i][j]:
						self.matrix[i][j] = self.matrix[i][k] + self.matrix[k][j]
						self.paths[i][j] = k

		return self

	def getItermediate(self, source, destination):
		if self.matrix[source][destination] == Infinity:
			raise NoSuchAPathError

		intermediate = self.paths[source][destination]

		if intermediate is None:
			return [ ]

		return (self.getItermediate(source, intermediate)
					+ [ intermediate ]
						+ self.getItermediate(intermediate, destination))

	def getPath(self, source, destination):
		return ([ source ]
					+ self.getItermediate(source, destination)
						+ [ destination ])

graph = [
	[0, 6, 8, 3, 5, 3, 2, 7, 1, 2, ],
	[0, 0, 2, 9, 1, 6, 2, 9, 9, 7, ],
	[6, 8, 0, 5, 8, 5, 7, 9, 8, 2, ],
	[6, 9, 7, 0, 8, 9, 8, 6, 3, 4, ],
	[0, 4, 8, 1, 0, 5, 8, 0, 7, 9, ],
	[2, 3, 3, 9, 9, 0, 0, 3, 0, 4, ],
	[7, 8, 0, 7, 7, 2, 0, 6, 0, 8, ],
	[3, 3, 5, 4, 8, 8, 8, 0, 4, 0, ],
	[9, 7, 2, 5, 0, 5, 4, 9, 0, 3, ],
	[6, 1, 8, 6, 6, 6, 1, 6, 7, 0, ],
]

print FloydWarshall(graph).shortestPaths().getPath(1,9)

########NEW FILE########
__FILENAME__ = bhaskara
# encoding: utf-8

"""
Bhaskara
Autor:
    Bhaskara Akaria [1]
Colaborador:
    Karlisson Bezerra
Tipo:
    math
Descrição:
    Calcula as raízes de uma equação de segundo grau
Complexidade:  
    O(1)
DIficuldade:
    facil
Referências:
    [1] http://pt.wikipedia.org/wiki/Bhaskara_Akaria
"""

import math

def bhaskara(a, b, c):
    delta = b ** 2 - 4 * a * c
    if delta < 0:
        return None
    else:
        raizes = []
        m1 = math.sqrt(delta)
        r1 =(-b + m1) / (2 * a)
        raizes.append(r1)
        r2 =(-b - m1) / (2 * a)
        raizes.append(r2)
        return raizes

print(bhaskara(1, -1, -2))

########NEW FILE########
__FILENAME__ = dda
'''
DDA (Digital Differential Analyzer)
Autor:
    ?
Colaborador:
    Jos� Ivan Bezerra Vilarouca Filho (ivanfilho2204@hotmail.com)
Tipo:
	math
Descri��o:
    DDA � um algoritmo de interpola��o linear entre dois pontos, inicial e final.
	Ele � muito usado na �rea de Computa��o Gr�fica para rasterizar linhas e pol�gonos.
Complexidade:  
    O(n)
Dificuldade:
    facil
Refer�ncias:
    http://www.dca.fee.unicamp.br/courses/IA725/1s2006/notes/n4.pdf
	http://en.wikipedia.org/wiki/Digital_Differential_Analyzer_(graphics_algorithm)
'''

import math

def DDA(x1, y1, x2, y2):
	
	points = [] #Guardar� os pontos criados na forma (x, y)
	
	if (math.fabs(x2 - x1) >= math.fabs(y2 - y1)):
		
		len = math.fabs(x2 - x1)
	else:
		
		len = math.fabs(y2 - y1)
	
	deltax = (x2 - x1) / len
	deltay = (y2 - y1) / len
	x = x1 + math.copysign(0.5, deltax)
	y = y1 + math.copysign(0.5, deltay)
	
	for i in range(int(len)) :
	
		points.append((math.floor(x), math.floor(y)))
		x += deltax
		y += deltay
	
	points.append((math.floor(x), math.floor(y)))
	
	return points

if __name__ == "__main__" :
	
	print DDA(-1, -1, 12, 9)
########NEW FILE########
__FILENAME__ = media-num
# -*- encoding: utf-8 -*-

"""
Media Numerica
Autor:
    ?
Colaborador:
	Bruno Lara Tavares <bruno.exz@gmail.com>
    Guilherme Carlos (@guiessence)
Tipo:
    math
Descrição:
    Calcula a média de numeros inseridos pelo usuário
Complexidade:  
    0(1)
Dificuldade:
    facil
"""

from __future__ import division

def media(*args):
	sum = 0
	for i in args:
		sum += i
	return sum / len(args)

#Adicione a quantidade de numeros que for preciso
print media(2,3,4,10)

########NEW FILE########
__FILENAME__ = media
# encoding: utf-8

"""
Cálculo da média ponderada
Autor:
    ?
Colaborador:
    Karlisson Bezerra
Tipo:
    math
Descrição:
    Calcula a média ponderada - é um algoritmo
    comum em qualquer curso de introdução à programação,
    que pode variar de acordo com os pesos.
Complexidade:  
    O(1)
Dificuldade:
    facil
"""

import math

def media(n1, n2, n3):
    p1, p2, p3 = 4, 5, 6
    return (n1 * p1 + n2 * p2 + n3 * p3) / (p1 + p2 + p3)

print media(7.0, 8.0, 10.0)

########NEW FILE########
__FILENAME__ = bisection-method
# encoding: utf-8
"""
Método da Bisseção
Autor:
    ?
Colaborador:
    Lucas Andrade (lucasfael@gmail.com)
Tipo:
    math
Descrição:
    Calcula a raiz aproximada de uma equação polinomial qualquer
    dentro de um intervalo até uma precisão desejada.
Complexidade:  
    O(log n)
Dificuldade:
    facil
Referências:
    http://www.im.ufrj.br/dmm/projeto/projetoc/precalculo/sala/conteudo/capitulos/cap114.html
    
"""

import math

def root(function, x0, x1, precision=0.0001):
    x0 *= 1.0
    x1 *= 1.0
    while (math.fabs(x0-x1) > precision):
        fx0 = function(x0)
        fx1 = function(x1)
        if (fx0 * fx1) > 0:
            return
        if fx0 == 0:
            return x0
        if fx1 == 0:
            return x1
        x2 = (x0 + x1) / 2
        fx2 = function(x2)
        if (fx0 * fx2) < 0:
            x1 = x2
        else:
            x0 = x2
    return x0

def funcao(x):
    return math.pow(x, 3)-(9 * x) + 3

x = root (funcao, 0, 1)
print x

########NEW FILE########
__FILENAME__ = matrix-transpose
# coding: utf-8
'''
Transposição de matrizes
Autor: 
    ?
Colaborador:
    Dayvid Victor (victor.dvro@gmail.com)
Tipo:
    math
Descrição: 
    Calcula a matriz tranposta de uma matriz qualquer, ou seja, a matriz
    resultante da troca das linhas pelas colunas.
Complexidade de tempo: 
    O(m*n)
Dificuldade: 
    facil
Referências:
    http://en.wikipedia.org/wiki/Transpose
'''

def get_transpose(matrix):
	return [[c for c in [l[i] for l in matrix]] for i in range(len(matrix[0]))]

if __name__ == '__main__':
	matrix = [[1,1,1],[2,2,2],[3,3,3],[4,4,4],[5,5,5]]
	print matrix
	print get_transpose(matrix)
	

########NEW FILE########
__FILENAME__ = bozofactoring
# encoding: utf-8

"""
Bozo factoring
Autor:
    Ricardo Bittencourt
Colaborador:
    Ricardo Bittencourt (bluepenguin@gmail.com)
Tipo:
    number-theory
Descrição:
    Calcula os fatores primos de um numero usando o pior algoritmo conhecido.
Complexidade:  
    O(n^n)
Dificuldade:
    medio
Referências:
    http://blog.ricbit.com/2010/07/o-algoritmo-mais-lento-do-oeste.html
Licenca:
    GPL
"""

import itertools

def factor(n):
  solutions = []
  for f in itertools.product(range(1,1+n),repeat=n):
    if reduce(lambda x,y: x*y, f) == n:
      solutions.append(filter(lambda x:x>1, list(f)))
  solutions.sort(key=len, reverse=True)
  return solutions[0]

print factor(6)

########NEW FILE########
__FILENAME__ = divisors
# * encoding: UTF-8 *

"""
Divisors
Autor:
    ?
Colaborador:
    ?
Descricao:
   Mostra os divisores de um número
Complexidade:
    O(n)
Dificuldade:
    facil
"""

n = int(raw_input("Digite um numero: "))
for i in range(1, n+1):
    if not n % i:
        print i,

########NEW FILE########
__FILENAME__ = eratosthenes
# -*- encoding: utf-8 -*-
"""
Crivo de Eratóstenes
Autor:
    Eratóstenes de Cirene
Colaborador:
    Juan Lopes (me@juanlopes.net)
Tipo:
    Exemplos: math
Descrição:
    Gera array de primalidade de inteiros através de algoritmo com baixa 
    complexidade.
Complexidade:  
    O(n loglogn)
Dificuldade:
    Médio
Referências: (opcional)
    http://en.wikipedia.org/wiki/Sieve_of_Eratosthenes
"""

from math import sqrt

def sieve(n):
    P = [True]*n
    P[0] = False
    P[1] = False
    
    for i in xrange(2, int(sqrt(n))):
        if P[i]:
            for j in xrange(i**2, n, i):
                P[j] = False
    return P

def primes_up_to(n):
    for i, p in enumerate(sieve(n)):
        if p: 
            yield i
    
print 'Primos ate 20:'
for i in primes_up_to(20):
    print i


########NEW FILE########
__FILENAME__ = euclid
# encoding: utf-8

"""
Algoritmo de Euclides
Autor:
    Euclides de Alexandria
Colaborador:
    Liquen 
Tipo:
    number-theory
Descrição:
    Algoritmo de Euclides em sua forma moderna. Computa o máximo
    divisor comum (MDC) entre dois números inteiros. Parte do princípio de
    que o MDC não muda se o menor número for subtraído do maior. [1] [2]
Complexidade:
    O(n^2), onde n é o número de dígitos da entrada. [3]
    O número de passos é no máximo
        log(max(a, b) * sqrt(5)) / log(phi),
    onde phi = 1.618... é a proporção áurea. [3]
Dificuldade:
    facil
Referências:
    [1] http://en.wikipedia.org/wiki/Euclidean_algorithm
    [2] http://pt.wikipedia.org/wiki/Algoritmo_de_Euclides
    [3] http://mathworld.wolfram.com/EuclideanAlgorithm.html
"""

def euclides(a, b):
    while b != 0:
        a, b = b, a % b
    return a

print(euclides(1071, 462))

########NEW FILE########
__FILENAME__ = fatorial
# encoding: utf-8

"""
Cálculo de fatorial
Autor:
    ?
Colaborador:
    Bruno Lara Tavares <bruno.exz@gmail.com>
Tipo:
    math
Descrição:
    Calcula o fatorial de um número
Complexidade:  
    ?
Dificuldade:
    facil
"""


def fatorial(b):
	return 1 if b <= 1 else b*fatorial(b-1)

print fatorial(6)

########NEW FILE########
__FILENAME__ = fibonacci-matrix-form
# coding: utf-8
"""
 * Sequência de Fibonacci
 *
 * Autor:
 *   Antonio Ribeiro <alvesjunior.antonio@gmail.com>
 * Tipo:
 *   math
 * Descrição:
 *   Na matemática, os Números de Fibonacci são uma sequência definida como recursiva.
 *   O algoritmo recursivo que define a série aplica-se, na prática, conforme a regra sugere: 
 *   começa-se a série com 0 e 1; a seguir, obtém-se o próximo número de Fibonacci somando-se 
 *   os dois anteriores e, assim, sucessiva e infinitamente.
 *
 *   Esta implementação baseia-se na propriedade de dividir-para-conquistar aplicada à
 *   potenciação de matrizes para acelerar o cálculo do número de fibonacci, reduzindo
 *   a complexidade do algoritmo para O(lg n)
 * Complexidade:
 *   O(lg n)
 * Dificuldade:
 *   Médio
 * Referências:
 *   http://assemblando.wordpress.com/2011/05/14/pela-uniao-dos-seus-poderes/
 *
"""

matriz_semente = [[1,1],[1,0]]

def pow_matriz(b,n):
    """Realiza a potenciação da matriz b pelo expoente n usando dividir-para-conquistar"""
    
    if n==1:
        return b

    if n%2:
        h = pow_matriz(b,(n-1)/2)
        return multi_matriz(multi_matriz(h,h),b)

    else:
        h = pow_matriz(b,n/2)
        return multi_matriz(h,h)


def multi_matriz(ma,mb):
    "Realiza a multiplicação de duas matrizes 2x2"

    (a,b),(c,d) = ma
    (e,f),(g,h) = mb
    return [[a*e+b*g,a*f+b*h],[c*e+d*g,c*f+d*h]]


def fibo(n):
    "Realiza (matriz_semente)^n e retorna o elemento da linha zero, coluna um"

    if n==0 or n==1:
        return n

    return pow_matriz(matriz_semente, n)[0][1]


if __name__=='__main__':
    for i in range(100):
        print fibo(i)

########NEW FILE########
__FILENAME__ = fibonacci
# -*- encoding: utf-8 -*-
"""
 * Sequência de Fibonacci
 *
 * Autor:
 *   Felipe Djinn <felipe@felipedjinn.com.br>
 * Colaborador:
 *   Bruno Lara Tavares <bruno.exz@gmail.com>
 *   Dilan Nery <dnerylopes@gmail.com>
 * Tipo:
 *   math
 * Descrição:
 *   Na matemática, os Números de Fibonacci são uma sequência definida como recursiva.
 *   O algoritmo recursivo que define a série aplica-se, na prática, conforme a regra sugere: 
 *   começa-se a série com 0 e 1; a seguir, obtém-se o próximo número de Fibonacci somando-se 
 *   os dois anteriores e, assim, sucessiva e infinitamente.
 * Complexidade:
 *   O(n)
 * Referências:
 *   http://pt.wikipedia.org/wiki/N%C3%BAmero_de_Fibonacci
 *
"""
def fibonacci(nesimo):
    c, n1, n2 = 0, 0, 1
    while c < nesimo:
        n1, n2 = n2, n1 + n2
        c += 1
    return n2

for nesimo in range(100):
	print fibonacci(nesimo)

########NEW FILE########
__FILENAME__ = miller-rabin
# -*- encoding: utf-8 -*-
"""
Teste de primalidade de Miller-Rabin
Autor:
    Gary L Miller e Michael O. Rabin
Colaborador:
    Juan Lopes (me@juanlopes.net)
Tipo:
    math
Descrição:
    Teste probabilistico de primalidade. Prova-se que para valores até 
    4.759.123.141, basta testar com as 'testemunhas' 2, 7 e 61. Este teste é 
    muito mais rápido do que testar através de 'trial division', principalmente 
    para números grandes.
Complexidade:  
    ?
Dificuldade:
    difícil
Referências: (opcional)
    http://en.wikipedia.org/wiki/Miller%E2%80%93Rabin_primality_test
"""

def witness(a, n):
   u,t= (n/2, 1)
   while(u%2==0): 
      u,t = (u/2, t+1)
      
   prev = pow(a,u,n);
   
   for i in xrange(t):
      curr=(prev*prev)%n
      if curr==1 and prev!=1 and prev!=n-1: return True
      prev=curr
      
   return curr != 1
 
def is_prime(n):
   if n in (0, 1): return False
   if n in (2, 7, 61): return True
   if witness(2,n): return False
   if witness(7,n): return False
   if witness(61,n): return False
   return True
    
print 'Primos ate 20:'
for i in xrange(1, 20):
    if is_prime(i):
        print i

print '2 147 483 647?', is_prime(2147483647)
print '2 147 483 648?', is_prime(2147483648)
        

########NEW FILE########
__FILENAME__ = perfectnumber
# encoding: utf-8
""" 
Números perfeitos
Autor: 
      ?
Colaborador:
      Anna Cruz (anna.cruz@gmail.com)
Tipo:
    math, number-theory
Descrição:
    Esse algoritmo serve para verificar se um número é perfeito ou não. Números perfeitos são aqueles cuja soma dos divisores (exceto ele mesmo) é igual ao próprio número, como por exemplo 6, cujos divisores são 1, 2 e 3 e 1+2+3 = 6
Complexidade:
      ?
Dificuldade:
      fácil
Referências:
      http://en.wikipedia.org/wiki/Perfect_numbers
"""

def calc_perf(number):
  counter = 1
  divisors = []
  sumarize = 0
  while counter <= number/2:
    if number%counter == 0:
      divisors.append(counter)
    counter += 1
  for divisor in divisors:
    temp = divisor
    sumarize += divisor
  if sumarize == number:
    print "This is a perfect number"
  else:
    print "This is not a perfect number try again"

calc_perf(8128)

########NEW FILE########
__FILENAME__ = pow
# coding: utf-8
'''
Exponenciação
Autor: 
    	?
Colaborador:
    	Dayvid Victor (victor.dvro@gmail.com)
Tipo:
    	math
Descrição: 
	calcula exponenciação
Complexidade de tempo: 
    	O(log n)
Dificuldade: 
    	fácil
Referências:
	?
'''
def pow(x, n):
	if n < 0:
		return float(1) / float(pow(x, -n))
	p = (pow(x, n/2) if n != 0 else 1)
	return (p * p if n % 2 == 0 else p * p * x)

print [pow(2,n) for n in range(11)]
print [pow(2,n) for n in range(-11,0)]




########NEW FILE########
__FILENAME__ = powmod
# coding: utf-8
'''
Exponenciação Modular
Autor: 
    ?
Colaborador:
    Juan Lopes <me@juanlopes.net>
Tipo:
    math
Descrição: 
    Calcula exponenciação modular de inteiros em tempo logaritmico.
        
    Baseia-se no fato de que:
    (a*b)%n == ((a%n) * (b%n)) % n
Complexidade de tempo: 
    O(log n)
Dificuldade: 
    fácil
Referências:
    ?
'''
def pow(x, e, m):
    if e==0: return 1
    p = pow(x,e/2,m)%m
    k = (1 if e%2==0 else x)
    return (p*p*k)%m

for i in range(20):
    print '3 ^ %d mod 1000 = %d (%d)' % (i, pow(3, i, 1000), 3**i)




########NEW FILE########
__FILENAME__ = stirling
# -*- encoding: utf-8 -*-
"""
 Fórmula de Stirling

 Autor:
   Pedro Menezes <eu@pedromenezes.com>
   DiogoK <diogo@diogok.net>
 Tipo:
   math
 Descrição:
   A Fórmula de Stirling estabelece uma aproximação assintótica para o fatorial de um número.
 Referências:
   http://pt.wikipedia.org/wiki/F%C3%B3rmula_de_Stirling
"""

from math import sqrt, pi, e, pow

def stirling(n):
    return sqrt(2*pi*n) * pow(n/e, n)

if __name__ == '__main__':
    for n in xrange(1, 10):
        print("fat %d ~ %f" %(n, stirling(n)))
########NEW FILE########
__FILENAME__ = helloworld
"""
Helloworld
Autor:
    ?
Colaborador:
    Karlisson - contato@nerdson.com
Tipo:
    misc
Descrição:
    Imprime a string Hello world
Complexidade:  
    O(1)
Dificuldade:
    facil
"""

print "Hello world"

########NEW FILE########
__FILENAME__ = inteval_scheduling
# -*- coding: utf-8 -*-

"""
Algoritmo guloso de agendamento de intervalos

Autor:

Colaborador:
	Pedro Arthur Duarte (JEdi)
	pedroarthur.jedi@gmail.com

Tipo:
	Interval Scheduling
	Greed Algorithms
	Optimization

Descrição:
	Dado um conjunto de tarefas expressos como t = (s,e), onde 's' especifica
	o inicio da tarefa e 'e' o seu fim, determinar o subconjunto máximo de
	tarefas que não se sobrepõem.

	Uma das maneiras de determinar esse subconjunto consiste em selecionar
	gulosamente as tarefas com base no seu horário de término: as tarefas com
	término mais cedo que não se sobrepõem são selecionadas para formar o
	subconjunto de saída.

Complexidade:
	O(n), para um conjunto de tarefas ordenadas;

	O(n) + O(g(n)), para um conjunto de tarefas não ordenadas, onde 'g' é
                    uma função de ordenação.

Dificuldade:
	Fácil

Referências:
	Kleinberg, Jon; Tardos, Eva (2006). Algorithm Design.
	ISBN 0-321-29535-8

Licença:
	GPLv3

"""

def intervalScheduling(tasks):
	# Cópia a lista de tarefas e a ordena. O método "sort" das listas Python
	# é local. Portanto, caso seja necessário a lista original, não devemos
	# chamá-lo sem antes cloná-la.
	tasks = tasks[:]
	tasks.sort()

	# A tarefa com termino mais cedo sempre é a primeira do subconjunto
	# de saída
	scheduling = [ tasks[0] ]

	# Agora, para todos os outros elementos da lista ordenada de tarefas, nós
	# verificamos se esse elemento é compatível com as tarefas já presentes
	# no subconjunto de saída. Para uma lista ordenada, essa operação é O(1)
	# pois necessita apenas acessar a última tarefa inserida.
	for t in tasks[1:]:
		# Se o momento de inicio da tarefa é maior ou igual ao fim da última
		# tarefa do subconjunto de saída, ela é compatível.
		if t.start >= scheduling[-1].end:
			# E, logo, nós a inserimos no subconjunto de saída
			scheduling.append(t)

	# Por último, retornamos a lista
	return scheduling

# Conjunto de tarefas de exemplo
#  --- ---- --------
# ---- --- - --- ----
#  ----  -- -- --- --
#   ---- --- ---- ---

class Task:
	'''
	Abstração das tarefas
	'''
	start = 0
	end = 0

	def __init__(self, start, end):
		self.start = start
		self.end = end

	def __repr__(self):
		return '''<Task %s:%s>''' % (self.start, self.end)

	def __cmp__(self, o):
		if self.end < o.end:
			return -1

		if self.end == o.end:
			if self.start < o.start:
				return -1
			elif self.start > o. start:
				return 0
			else:
				return 1

		return 1

# Em formato de lista
tasks = [ Task(40, 70), Task(80, 120), Task(130, 210),
 Task(30, 70), Task(80, 110), Task(120, 130), Task(140, 170), Task(180, 220),
 Task(40, 80), Task(100, 120), Task(130, 150), Task(160, 190), Task(200, 220),
 Task(50, 90), Task(100, 130), Task(140, 180), Task(190, 220) ]

print intervalScheduling(tasks)

########NEW FILE########
__FILENAME__ = knapsack
# -*- coding: utf-8 -*-

"""
Algoritmo da Mochila

Autor:

Colaborador:
	Pedro Arthur Duarte (JEdi)
	pedroarthur.jedi@gmail.com

Tipo:
	0-1 Knapsack Problem
	Unbounded Knapsack
	Dynamic Programming

Descrição:
 	Dado uma conjunto de itens $I$ onde cada item $i$ possui um peso $p_i$ e um
	benefício $b_i$ associado, e uma mochila de carga máxima $m$, maximizar o
	benefício provido por uma combinação de itens respeitando a carga máxima
	suportda pela mochila. Em outras, palavras,
	satisfazer ao seguinte problema de otimização:
	%
	\begin{itemize}
		\item[] Maximizar $$\sum_{i=1}^{n} b_i x_i$$
		\item[] com a restrição $$\sum_{i=1}^{n} p_i x_i \le m$$
	\end{itemize}
	%
	onde $x_i$ é no número de repetiçoes do item $i$. A versão mais simples do
	problema, com cada item repetindo-se no máximo uma vez, ou $x_i \le 1$, é
	conhecida como 0-1 Knapsack. Instâncias sem essa limitação são conhecidas
	como Unbounded Knapsack.

    % OBS: a descrição acima é melhor visualizada após processada pelo LaTeX.
    % Visite http://scribtex.com/ para um compilador on-line

Complexidade:
	O(nm),	pseudo-polinomial no tempo, onde 'n' é cardinalidade do conjunto de
			item e 'm' é a carga máxima da mochila.

	O(nm),	pseudo-polinomial no espaço para o 0-1 Knapsack
	 O(m),	pseudo-polinomial no espaço para o Unbounded Knapsack

Dificuldade:
	Média

Referências:
	Robert Sdgewick. Algorithms in C. ISBN 0-201-51425-7
	https://secure.wikimedia.org/wikipedia/en/wiki/Knapsack_problem

Licença:
	GPLv3

"""

class Item:
	def __init__(self, value, weight, label=None):
		self.value = value
		self.weight = weight

		if label == None:
			self.label = str((self.value, self.weight))
		else:
			self.label = label

	def __repr__(self):
		return '<Item ' + self.label + '>'

class Knapsack:
	def __init__(self, maxWeight, items=None):
		self.maxWeight = maxWeight
		self.items = items

	def zeroOne(self, items=None):
		'''
		Essa instância do problema da mochila possuí subestrutura ótima. Logo,
		é passível de resolução através de programação dinâmica. A seguinte
		formulação nos permite resolver esse problema numa abordagem bottom-up:

		% obs: LaTex code
		\[
			M[i,j] = \left\{
				\begin{array}{l l}
					M[i-1,j] & \text{se } p_i < j \\
					max(M[i-1,j], M[i,j-p_i] + b_i) & \text{se } p_i \ge j\\
				\end{array}
			\right.
		\]
		%
		Onde $M$ é uma matriz $n \times m$, $n$ é cardinalidade do conjunto
		de itens e $m$ a capacidade máxima da mochila.
		'''
		if not items:
			items = self.items

		M = [[ 0 ] * (self.maxWeight+1)]

		for i,item in enumerate(items, start=1):
			M.append([ 0 ] * (self.maxWeight+1))

			for w in xrange(1, self.maxWeight+1):
				if item.weight <= w:
					if M[i-1][w] > M[i-1][w-item.weight] + item.value:
						M[i][w] = M[i-1][w]
					else:
						M[i][w] = M[i-1][w-item.weight] + item.value
				else:
					M[i][w] = M[i-1][w]

		'''
		$M[n,m]$ nos informa o máximo benefício obtido. Porém, para recuperar
		a lista de itens escolhidos, Precisamos analisar a matriz $M$ mais a
		fundo.

		Caso o benefício da mochila com configuração $M[i,m]$ seja diferente do
		benefício da mochila com configuração $M[i-1,m]$, o item $i$ está entre
		os itens escolhidos. Assim, devemos continuar nossa busca na posição
		$M[i-1,m-p_i]$. Caso contrário, o item $i$ não está em nossa mochila e
		devemos continuar a busca na posição $M[i-1,m]$.

		O código abaixo o descrito acima.
		'''
		i,m = len(items), self.maxWeight
		output = [ ]

		while m > 0:
			if M[i][m] != M[i-1][m]:
				output.append(items[i-1])
				m = m - items[i-1].weight

			i = i - 1

		return M[-1][-1], output

	def unbounded(self, items=None):
		'''
		Essa instância do problema também possuí subestrutura ótima. Logo,
		também é passível de resolução através de programação dinâmica. A
		seguinte formulação nos permite resolver esse problema numa abordagem
		bottom-up:

		% obs: LaTex code
		$$ \displaystyle
		M[j] = max(M[j-1], ~\max_{\forall i \in I | p_i < j}(b_i + M[j-p_i]))
		$$
		%
		Onde $M$ é uma arranjo de cardinalidade $m$ e $m$ é a capacidade
		máxima da mochila.
		'''
		if not items:
			items = self.items

		M = [0] * (self.maxWeight+1)
		# Para que possamos recupera a lista de itens escolhidos, precisamos
		# de um arranjo auxiliar para armazenar a melhor escolha para a mochila
		# de tamanho 'j'.
		c = [None] * (self.maxWeight+1)

		for i,item in enumerate(items, start=1):
			for j in xrange(1, self.maxWeight+1):
				if item.weight <= j:
					if M[j] < M[j-item.weight] + item.value:
						M[j] = M[j-item.weight] + item.value
						c[j] = item

		'''
		Conceitualmente, $c[m]$ sempre está na mochila. Agora, para recuperar o
		restante dos itens, pasta decrementar m pelo peso do do item na posição
		em questão ($m = m - p_{c[m]}$)
		'''
		m = self.maxWeight
		output = [ ]

		while m > 0:
			output.append(c[m])
			m = m - c[m].weight

		return M[-1], output

items = [
	Item(15,2), Item(5,1), Item(20,3), Item(60,2)
]

k = Knapsack(6, items)

print k.zeroOne()
print k.unbounded()
########NEW FILE########
__FILENAME__ = AhoCorasick
# -*- coding: utf-8 -*-

"""
Algoritmo de Aho-Corasick.

Autor:
	Alfred Aho and Margaret Corasick (1975)

Colaborador:
	Pedro Arthur Duarte (JEdi)
	pedroarthur.jedi@gmail.com

Tipo:
	multi pattern string matching
	finite automate-based

Descrição:
	Dado um conjunto de padrões, esse algoritmo constrói uma máquina de estados
	finitos de forma que seja possível buscá-los no texto de entrada em tempo
	linearmente proporcional ao tamanho dessa última. Para isso, o algoritmo de
	Aho-Corasick utiliza uma estrutura de dados semelhante as Tries, porém com
	nós adicionais que evitam a necessidade de backtracking. Esse nós
	adicionais representam o maior prefixo comum presente entre os padrões.

Complexidade:
	O(⅀m) de pré-processamento, onde "m" é o tamanho do padrão
	O(n)  de busca, onde "n" é o tamanho do texto de entrada

Dificuldade:
  média (?)

Referências:
  https://en.wikipedia.org/wiki/Aho-Corasick_algorithm

Licença:
  GPLv3

"""

class AhoCoraski(dict):
	failTransition = None
	isTerminal = False

	def __init__(self, patternList=None, thenBuild=False):
		if patternList is not None:
			self.add(patternList)

		if thenBuild is True:
			self.build()

	def add(self, pattern):
		if isinstance(pattern, list):
			for w in pattern:
				self.add(w)

			return self

		currentState = self

		for c in pattern:
			if c not in currentState:
				currentState[c] = AhoCoraski()

			currentState = currentState[c]

		currentState.isTerminal = pattern

		return self

	def build(self):
		queue = [ self ]

		while len(queue) > 0:
			current = queue.pop(0)

			for transition, next in current.iteritems():
				state = current.failTransition

				while state is not None and transition not in state:
					state = state.failTransition

				if state is not None:
					next.failTransition = state[transition]
				else:
					next.failTransition = self

				queue.append(next)

		return self

	def match(self, subject):
		output = [ ]
		current = self

		if isinstance(subject, list):
			for s in subject:
				output += self.match(s)

			return output

		for c in subject:
			if c in current:
				current = current[c]
			else:
				current = current.failTransition

				while current is not None and c not in current:
					current = current.failTransition

				if current is not None:
					current = current[c]
				else:
					current = self

			if current.isTerminal is not False:
				output.append(current.isTerminal)

		return output

patternList = [ 'he', 'she', 'his', 'her', 'show', 'shall', 'hall', ]

print AhoCoraski(patternList, True).match("This phrase shall match")

########NEW FILE########
__FILENAME__ = kmp
# -*- encoding: utf-8 -*-
"""
KMP (Knuth-Morris-Pratt) algorithm
Autor:
    Donald Knuth, Vaughan Pratt and James H. Morris
Colaborador:
    Juan Lopes (me@juanlopes.net)
Tipo:
    pattern-matching
Descrição:
    Encontra todas as instâncias de P em Q em tempo linear.
    Usa tabela de lookup inicializada por P.
Complexidade:  
    O(n+m)
Dificuldade:
    Médio
Referências: (opcional)
    http://en.wikipedia.org/wiki/KMP_algorithm
"""

def kmp_init(P):
    F = [0]*(len(P)+1)
    i, j= 1, 0;
    while i<len(P):
        if P[i] == P[j]: 
            i+=1; j+=1; F[i] = j
        elif j == 0: 
            i+=1; F[i] = 0;
        else:            
            j = F[j];
    return F
    
def kmp(Q, P):
    F = kmp_init(P)
   
    i,j,n,m = 0,0,len(Q),len(P)
    
    while i-j <= n-m:
        while j < m:
            if P[j] == Q[i]: i+=1; j+=1
            else: break
        
        if j == m: yield i-m;
        elif j == 0: i+=1;
        j = F[j];


print list(kmp("casacasacasa", "casa")) #0, 4, 8
print list(kmp("cacacacacaca", "caca")) #0, 2, 4, 6, 8
########NEW FILE########
__FILENAME__ = levenshtein
# coding: utf-8
'''
Distância Levenshtein
Autor:
    Vladimir Levenshtein (1965)
Colaborador:
    Flávio Juvenal da Silva Junior (flaviojuvenal@gmail.com)
Descricao:
    A distância Levenshtein ou distância de edição entre duas strings
    é dada pelo número mínimo de operações necessárias para transformar
    uma string na outra. Entendemos por operações a inserção, deleção ou
    substituição de um caractere. Dessa forma, essa distância mede a
    quantidade de diferença entre duas strings (quanto maior, mais diferentes).
    E por isso é útil para aplicações de casamento de padrões, como
    corretores ortográficos.
Complexidade:
    O(len(s) * len(t)), onde s e t são as strings
Dificuldade:
    médio
Referências:
    http://en.wikipedia.org/wiki/Levenshtein_distance
    http://www.csse.monash.edu.au/~lloyd/tildeAlgDS/Dynamic/Edit/
Licenca:
    MIT
'''

def levenshtein(s, t):
    '''
    Implementação da versão não-recursiva do algoritmo.
    Veja em: http://en.wikipedia.org/wiki/Levenshtein_distance#Computing_Levenshtein_distance
    Observação: os -1 nas linhas 49 e 60 são porque em Python os índices
    das listas começam em 0.
    '''
    m = len(s) + 1
    n = len(t) + 1
    from_0_to_m = range(m)
    from_0_to_n = range(n)
    d = [[0]*n for _ in from_0_to_m]
    
    for i in from_0_to_m:
	d[i][0] = i
    for j in from_0_to_n:
	d[0][j] = j
    
    from_1_to_m = from_0_to_m[1:]
    from_1_to_n = from_0_to_n[1:]
    for j in from_1_to_n:
	for i in from_1_to_m:
	    if s[i-1] == t[j-1]:
		d[i][j] = d[i-1][j-1] #nenhuma operação necessária
	    else:
		d[i][j] = min(
		    d[i-1][j] + 1,   #uma exclusão
		    d[i][j-1] + 1,   #uma inserção
		    d[i-1][j-1] + 1, #uma substituição
		)
    return d[m-1][n-1]

if __name__ == '__main__':
    s = "kitten"
    t = "sitting"
    result = levenshtein(s, t)
    expected_result = 3
    #3, já que deve trocar k por s, e por i e inserir g
    assert result == expected_result
    print result

########NEW FILE########
__FILENAME__ = ballistic
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Balistica
Autor:
    ?
Colaborador:    
    GabrielBap <gabrielbap1@gmail.com>
Tipo:
    physics
Descrição:
    Informa a distância horizontal quem um projétil atingiu baseado na força aplicada, força da gravidade e ângulo da força.
Complexidade:
    0(1)
Dificuldade:
    facil
Referências:
    [1]http://www.algosobre.com.br/fisica/balistica-e-lancamento-de-projetil.html
"""

from math import pi, sin, cos, radians

def simula_tiro(angle, forca, gravidade, startY):
   
   angleR = radians(angle) # As funções sin e cos trabalham com radianos
   
   time = 0 # tempo inicial do tiro
   # Define os vetores de força vertical e horizontal
   VetorVertical = sin(angleR) * forca
   VetorHorizontal = cos(angleR) * forca
   # Pow!
   Y = startY
   X = 0
   while Y > 0: # Enquanto a bala não cair...
      X = VetorHorizontal * time # Distância atual em X (S = V * t)
      Y = startY + (VetorVertical * time) - (gravidade * (time**2)) # Distância atual em Y (S = S0 + V*t + (a * t^2)/2)
      time += 1
   
   return angle, X, Y

forca = float(raw_input("Qual será a força? "))
gravidade = float(raw_input("Qual será a força da gravidade? "))
startY = float(raw_input("Qual será a altura do canhão? "))
try:
   angle = float(raw_input("Qual será o ângulo? (Opcional) "))
   dados = simula_tiro(angle, forca, gravidade, startY)
   resultado = "Ângulo = %i\n X = %.5f\n Y = %.5f\n\n" % (dados[0], dados[1], dados[2])
   print resultado
except:  
   for angle in range(0,91): # Faz a simulação em todos os ângulos de 0 a 90
      dados = simula_tiro(angle, forca, gravidade, startY)
      resultado = "\nÂngulo = %i\nX = %.5f\nY = %.5f\n" % (dados[0], dados[1], dados[2])
      print resultado

########NEW FILE########
__FILENAME__ = binary-search
# coding: utf-8
'''
Busca Binária

Autor: 
    	Jon Bentley
Colaborador:
    	Dayvid Victor (victor.dvro@gmail.com)
Tipo:
	search
Descrição: 
	Faz uma busca em um vetor ordenado, usando o recurso
	'dividir para conquistar'. Ele compara o valor a ser
	buscado com o centro do vetor, se for menor, o mesmo
	procedimento é feito com o sub-vetor da esquerda, se
	for maior, com o sub-vetor da direita.	
Complexidade de tempo: 
    O(log n)
Dificuldade: 
    fácil
Referências:
	http://pt.wikipedia.org/wiki/Pesquisa_binária
'''

def binary_search(value, l):
	if len(l) == 0:
		return None
	mid = len(l)/2
	if value < l[mid]:
		return binary_search(value, l[:mid])
	elif value > l[mid]:
		tmp = binary_search(value, l[(mid + 1):])
		return (tmp is not None) and tmp + mid + 1 or None
	
	return mid

l = [0,1,2,3,4,7]
print binary_search(-1,l)
print binary_search(0,l)
print binary_search(1,l)
print binary_search(2,l)
print binary_search(3,l)
print binary_search(4,l)
print binary_search(5,l)
print binary_search(6,l)
print binary_search(7,l)
print binary_search(8,l)
print binary_search(9,l)








########NEW FILE########
__FILENAME__ = linear-search
# encoding: utf-8


"""
  Linear Search
Autor:
    ?
Colaborador:
    Bruno Lara Tavares <bruno.exz@gmail.com>
    José Alberto O. Morais Filho (j.moraisg12@gmail.com)
Tipo:
    search
Descrição:
    Utiliza força bruta em um array para retornar a posição de um valor nesse array, ou retornar -1, se nada
  for encontrado.
Complexidade:
    O(n)
Dificuldade:
    fácil
"""

# Entrada:
#   array = vetor onde o valor será pesquisado
#   search = valor procurado
# Saída:
#   a posição da primeira ocorrência do valor, ou -1, caso o valor não for encontrado

def linear_search(array, search):
  for k,v in enumerate(array):
    if v == search:
      return k
  
  return -1

# Exemplos

a = [1,5, 6, 3, 7,4]

print linear_search(a, 6)
print linear_search(a, 60)


########NEW FILE########
__FILENAME__ = token
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Token

Autor:
    ?
Colaborador:
    Felipe Djinn <felipe@felipedjinn.com.br>
Tipo:
    sequence
Descrição:
    Gera um token aleatório
Complexidade:
    ?
Dificuldade:
    facil
"""

import random
import string

def token(length = 10):
 return ''.join(random.choice(string.letters) for i in xrange(length)) 


"""
Examples
"""

print "Token com 10 caracteres (padrão): " + token()
print "Token com 5 caracteres: " +token(5)
print "Token com 15 caracteres " +token(15)

########NEW FILE########
__FILENAME__ = bozosort
# encoding: utf-8

"""
Bozosort
Autor:
    Bozo
Colaborador:
    Karlisson Bezerra
Tipo:
    sorting
Descrição:
    Embaralha um vetor indefinidamente, até que os números estejam em ordem.
Complexidade:  
    O(infinito)
Dificuldade:
    facil
Referências:
    http://nerdson.com/blog/libbozo-01/
    http://pt.wikipedia.org/wiki/Bogosort
"""

from random import shuffle

def is_sorted(seq):
  # We define an empty sequence to be sorted by default.
  if not seq:
      return True

  # Otherwise, the sequence is sorted if every element is less or equal
  # than the next one.
  last = seq[0]
  for element in seq:
      if last > element:
          return False
      last = element
  return True

def bozosort(seq):
    while not is_sorted(seq):
        shuffle(seq)
    return seq

print bozosort([2,4,9,1,0,-4,17,8,0,23,67,-1])

########NEW FILE########
__FILENAME__ = bubblesort
# encoding: utf-8

"""
Bubblesort
Autor:
    ?
Tipo:
    sorting
Descrição:
    Varre o vetor comparando cada um dos pares de números
    possíveis e trocando suas posições no vetor se necessário
Complexidade:  
    Pior caso: O(n²)
    Melhor caso: O(n²)
Dificuldade:
    facil
Referências:
    http://en.wikipedia.org/wiki/Bubble_sort
"""

def bubble(lst):
    for i, val1 in enumerate(lst):
        for j, val2 in enumerate(lst):
            if lst[i] < lst[j]:
               lst[i], lst[j] = lst[j], lst[i]
    return lst

print bubble([6, -7, 1, 12, 9, 3, 5])

########NEW FILE########
__FILENAME__ = dropsort
#!/usr/bin/env python2
# -*- coding: utf-8 -*- 
"""
Nome do algoritmo
Autor:
    David Morgan-Mar. <dmm@dangermouse.net>
Colaborador:
    Vinícius dos Santos Oliveira <vini.ipsmaker@gmail.com>
Tipo:
    sorting
Descrição:
    Dropsort é um algoritmo de ordernação lossy (causa perdas de informações)
    rápido, one-pass (lê a entrada exatamente uma vez, em ordem)

    O dropsort itera sobre os elementos da lista e, quando encontra um elemento
    menor que o anterior, descarta-o.
Complexidade:  
    O(n)
Dificuldade:
    facil
Referências:
    http://www.dangermouse.net/esoteric/dropsort.html
    http://students.cs.ndsu.nodak.edu/~abrjacks/dropsort.php (otimizações)
Licenca:
    MIT
"""

def dropsort(lst):
    i = 0
    prev = None
    while i != len(lst):
        if prev > lst[i]:
            del lst[i]
        else:
            prev = lst[i]
            i += 1

    return lst

if __name__ == '__main__':
    if dropsort([]) != []:
        exit(1)

    if dropsort([1, 2, 5, 3, 4, 6]) != [1, 2, 5, 6]:
        exit(1)

    if dropsort([1, 2, 2, 4]) != [1, 2, 2, 4]:
        exit(1)

    if dropsort([2, 11, 9, 8, 5, 4, 10, 3, 6, 0, 7, 13, 1, 12]) != [2, 11, 13]:
        exit(1)

########NEW FILE########
__FILENAME__ = insertionsort
#!/usr/bin/env python
# encoding: utf-8

'''
Insertion Sort
Autor: 
    ?
Tipo:
    sorting
Descrição:
    Percorre uma lista da esquerda para direita e vai deixando os elementos
    mais a esquerda ordenados à medida que avança pela lista.
Complexidade:
    Pior caso: O(n²)
    Melhor caso: O(n)
Dificuldade:
    Facil
Referencia:
    http://pt.wikipedia.org/wiki/Insertion_sort
'''

def insertion_sort(L):
    for i in range(1, len(L)):
        elemento = L[i]
        j = i - 1

        while j >= 0 and L[j] > elemento:
            L[j+1] = L[j]
            j -= 1
            L[j+1] = elemento

    return L

########NEW FILE########
__FILENAME__ = masochisticsort
#!/usr/bin/env python
# coding: utf-8

"""
Masochistic Sort
Author:
    Dilan Nery <dnerylopes AT gmail DOT com>
Colaborador:
    Dilan Nery <dnerylopes AT gmail DOT com>
Tipo:
    Ordenação
Descrição:
    Testa todas combinações possiveis de uma lista até encontrar a combinação
    em que a lista esteja ordenada
Complexidade:
    ?
Dificuldade:
    medio
Licensa:
    LGPL
"""

def masoquist_sort(L):
    if len(L) == 1:
        yield L
    elif len(L) == 2:
        count = 0
        while count < 2:
            L[0],L[1] = L[1],L[0]
            yield L
            count += 1
    else:
        for i in range(len(L)):
            L_copy = L[:]
            key = L_copy.pop(i)
            invert = masoquist_sort(L_copy)

            for i in invert:
                yield [key] + i
                
def is_sorted(L):
    flag = True
    for i in range(1,len(L)):
        if L[i-1] > L[i]:
            flag = False
    return flag                

if __name__ == '__main__':
    teste1 = masoquist_sort([2,4,1,5,4])
    for t1 in teste1:
        if is_sorted(t1):
            print t1
            break

    teste2 = masoquist_sort([2, 11, 9, 8, 5, 4, 10, 3, 6, 0, 7, 13, 1, 12])
    for t2 in teste2:
        if is_sorted(t2):
            print t2
            break

########NEW FILE########
__FILENAME__ = mergesort
# coding: utf-8

"""
Mergesort
Autor:
	John von Neumann, em 1945
Colaborador:
	Adriano Melo (adriano@adrianomelo.com)
	Dayvid Victor (victor.dvro@gmail.com)
Tipo:
	sorting
Descrição:
	O algoritmo ordena um vetor dividindo-o pela metade e, depois de processar
	cada metade recursivamente, intercala as metades ordenadas.
Complexidade:
	O (n*log(n))
Dificuldade:
	fácil
Referências:
	?
"""

def intercala (inicio, fim):
	result = []
	i, j   = 0, 0

	while i < len(inicio) and j < len(fim):
		if inicio[i] < fim[j]:
			result.append(inicio[i])
			i = i + 1

		elif inicio[i] >= fim[j]:
			result.append(fim[j])
			j = j + 1

	result = result + inicio[i:]
	result = result + fim [j:]
	
	return result

def mergesort(array):
	tamanho = len(array)

	if tamanho == 1:
		return array

	inicio = mergesort (array[0:tamanho/2])
	fim    = mergesort (array[tamanho/2:])

	return intercala (inicio, fim)

print mergesort ([2,8,-2,1,45,37,-463,24,50,80,4,3,7,4,55])
print mergesort ([8,7,3,4,5])



########NEW FILE########
__FILENAME__ = quicksort
# coding: utf-8
"""
Quicksort
Autor:
    C.A.R. Hoare
Colaborador:
    Adriano Melo (adriano@adrianomelo.com)
    Juan Lopes (me@juanlopes.net)
Tipo:
    sorting
Descrição:
    Quicksort é um algorítmo de ordenação de vetores cuja estratégia é
    dividir para conquistar. Basicamente o algorítmo organiza os elementos
    dos vetores de forma que os menores estejam antes dos maiores.
    Esse passo é feito recursivamente até que a lista completa esteja ordenada.
Complexidade:  
    O(n log(n)) - Melhor caso e médio caso.
    O(n²) - Pior caso.
Dificuldade:
    facil
Referências: (opcional)
    http://pt.wikipedia.org/wiki/Quicksort
"""
from random import randint

def quicksort(V):
    if len(V) <= 1: 
        return V
    
    pivot = V[0]
    equal = [x for x in V if x == pivot]
    lesser = [x for x in V if x < pivot]
    greater = [x for x in V if x > pivot]
    return quicksort(lesser) + equal + quicksort(greater)

print quicksort([i for i in xrange(30)]) # worst case
print quicksort([3 for i in xrange(30)]) # best case
print quicksort([randint(-100, 400) for i in xrange(30)]) # average case


########NEW FILE########
__FILENAME__ = selectionsort
# encoding: utf-8
'''
Insertion Sort
Autor:
    ?
Colaborador:
	Bruno Coimbra <bbcoimbra@gmail.com>
Tipo:
    sorting
Descrição:
	Percorre uma lista a procura do menor valor e inclui na posição correta.
Complexidade:
	O(n²)
Dificuldade:
    Facil
Referencia:
    http://pt.wikipedia.org/wiki/Selection_sort
'''
from random import randint

def selectionsort(L):
	for i in range(0, len(L)):
		minor = L[i]
		minor_pos = i
		for j in range(i+1, len(L)):
			if L[j] < minor:
				minor = L[j]
				minor_pos = j
		L[i], L[minor_pos] = minor, L[i]
	return L

A = [randint(1, 50) for i in range(30)]
print A
print selectionsort(A)


########NEW FILE########
__FILENAME__ = sleepsort
# -*- coding: utf-8 -*-

"""
Sleepsort
Autor:
    ?
Colaborador:
    Saulo Andrade Almeida <sauloandrade@gmail.com>
Tipo:
    sorting
Descrição:
    Uma brincadeira sobre ordenacao numerica baseada em threads e sleep.
    O algoritimo dispara threads para cada numero que sera ordenado com o 
    tempo de espera baseado no valor do numero, ou seja quanto maior o 
    numero mais ele demora para acordar e ser reinserido na nova estrututa 
    ordenada.

    Para utilizar o algoritimo basta executar o arquivo e uma lista padrao 
    sera executado, ou informar um lista de valores separados por espacos.
    Ex: $ python sleepsort.py ou $ python sleepsort 4 7 3 9 8 1 2
Complexidade:  
    ?
Dificuldade:
    facil
Referências: (opcional)
    Adaptado de http://dis.4chan.org/read/prog/1295544154
"""

import sys, time, threading

def sleepit(val):
    time.sleep(val/4.0)
    print val

# se nao vier parametro, usa uma lista padrao
if not sys.argv[1:] :
    values = [7,9,2,5,6,4,1,8,3]

# se vier, usa a lisra informada
else:
    values = sys.argv[1:]

# loop que dispara as threads    
print "Ordenando a lista ", values
[ threading.Thread(target=sleepit, args=[int(a)]).start() for a in values ]

########NEW FILE########
