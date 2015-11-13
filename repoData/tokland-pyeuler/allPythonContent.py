__FILENAME__ = data
import os

datadir = os.path.dirname(__file__)

def openfile(filename):
    """Return filename from data directory."""
    return open(os.path.join(datadir, filename))
  
problem8 = """
73167176531330624919225119674426574742355349194934
96983520312774506326239578318016984801869478851843
85861560789112949495459501737958331952853208805511
12540698747158523863050715693290963295227443043557
66896648950445244523161731856403098711121722383113
62229893423380308135336276614282806444486645238749
30358907296290491560440772390713810515859307960866
70172427121883998797908792274921901699720888093776
65727333001053367881220235421809751254540594752243
52584907711670556013604839586446706324415722155397
53697817977846174064955149290862569321978468622482
83972241375657056057490261407972968652414535100474
82166370484403199890008895243450658541227588666881
16427171479924442928230863465674813919123162824586
17866458359124566529476545682848912883142607690042
24219022671055626321111109370544217506941658960408
07198403850962455444362981230987879927244284909188
84580156166097919133875499200524063689912560717606
05886116467109405077541002256983155200055935729725
71636269561882670428252483600823257530420752963450
"""

problem11 = """
08 02 22 97 38 15 00 40 00 75 04 05 07 78 52 12 50 77 91 08
49 49 99 40 17 81 18 57 60 87 17 40 98 43 69 48 04 56 62 00
81 49 31 73 55 79 14 29 93 71 40 67 53 88 30 03 49 13 36 65
52 70 95 23 04 60 11 42 69 24 68 56 01 32 56 71 37 02 36 91
22 31 16 71 51 67 63 89 41 92 36 54 22 40 40 28 66 33 13 80
24 47 32 60 99 03 45 02 44 75 33 53 78 36 84 20 35 17 12 50
32 98 81 28 64 23 67 10 26 38 40 67 59 54 70 66 18 38 64 70
67 26 20 68 02 62 12 20 95 63 94 39 63 08 40 91 66 49 94 21
24 55 58 05 66 73 99 26 97 17 78 78 96 83 14 88 34 89 63 72
21 36 23 09 75 00 76 44 20 45 35 14 00 61 33 97 34 31 33 95
78 17 53 28 22 75 31 67 15 94 03 80 04 62 16 14 09 53 56 92
16 39 05 42 96 35 31 47 55 58 88 24 00 17 54 24 36 29 85 57
86 56 00 48 35 71 89 07 05 44 44 37 44 60 21 58 51 54 17 58
19 80 81 68 05 94 47 69 28 73 92 13 86 52 17 77 04 89 55 40
04 52 08 83 97 35 99 16 07 97 57 32 16 26 26 79 33 27 98 66
88 36 68 87 57 62 20 72 03 46 33 67 46 55 12 32 63 93 53 69
04 42 16 73 38 25 39 11 24 94 72 18 08 46 29 32 40 62 76 36
20 69 36 41 72 30 23 88 34 62 99 69 82 67 59 85 74 04 36 16
20 73 35 29 78 31 90 01 74 31 49 71 48 86 81 16 23 57 05 54
01 70 54 71 83 51 54 69 16 92 33 48 61 43 52 01 89 19 67 48
"""

problem13="""
37107287533902102798797998220837590246510135740250
46376937677490009712648124896970078050417018260538
74324986199524741059474233309513058123726617309629
91942213363574161572522430563301811072406154908250
23067588207539346171171980310421047513778063246676
89261670696623633820136378418383684178734361726757
28112879812849979408065481931592621691275889832738
44274228917432520321923589422876796487670272189318
47451445736001306439091167216856844588711603153276
70386486105843025439939619828917593665686757934951
62176457141856560629502157223196586755079324193331
64906352462741904929101432445813822663347944758178
92575867718337217661963751590579239728245598838407
58203565325359399008402633568948830189458628227828
80181199384826282014278194139940567587151170094390
35398664372827112653829987240784473053190104293586
86515506006295864861532075273371959191420517255829
71693888707715466499115593487603532921714970056938
54370070576826684624621495650076471787294438377604
53282654108756828443191190634694037855217779295145
36123272525000296071075082563815656710885258350721
45876576172410976447339110607218265236877223636045
17423706905851860660448207621209813287860733969412
81142660418086830619328460811191061556940512689692
51934325451728388641918047049293215058642563049483
62467221648435076201727918039944693004732956340691
15732444386908125794514089057706229429197107928209
55037687525678773091862540744969844508330393682126
18336384825330154686196124348767681297534375946515
80386287592878490201521685554828717201219257766954
78182833757993103614740356856449095527097864797581
16726320100436897842553539920931837441497806860984
48403098129077791799088218795327364475675590848030
87086987551392711854517078544161852424320693150332
59959406895756536782107074926966537676326235447210
69793950679652694742597709739166693763042633987085
41052684708299085211399427365734116182760315001271
65378607361501080857009149939512557028198746004375
35829035317434717326932123578154982629742552737307
94953759765105305946966067683156574377167401875275
88902802571733229619176668713819931811048770190271
25267680276078003013678680992525463401061632866526
36270218540497705585629946580636237993140746255962
24074486908231174977792365466257246923322810917141
91430288197103288597806669760892938638285025333403
34413065578016127815921815005561868836468420090470
23053081172816430487623791969842487255036638784583
11487696932154902810424020138335124462181441773470
63783299490636259666498587618221225225512486764533
67720186971698544312419572409913959008952310058822
95548255300263520781532296796249481641953868218774
76085327132285723110424803456124867697064507995236
37774242535411291684276865538926205024910326572967
23701913275725675285653248258265463092207058596522
29798860272258331913126375147341994889534765745501
18495701454879288984856827726077713721403798879715
38298203783031473527721580348144513491373226651381
34829543829199918180278916522431027392251122869539
40957953066405232632538044100059654939159879593635
29746152185502371307642255121183693803580388584903
41698116222072977186158236678424689157993532961922
62467957194401269043877107275048102390895523597457
23189706772547915061505504953922979530901129967519
86188088225875314529584099251203829009407770775672
11306739708304724483816533873502340845647058077308
82959174767140363198008187129011875491310547126581
97623331044818386269515456334926366572897563400500
42846280183517070527831839425882145521227251250327
55121603546981200581762165212827652751691296897789
32238195734329339946437501907836945765883352399886
75506164965184775180738168837861091527357929701337
62177842752192623401942399639168044983993173312731
32924185707147349566916674687634660915035914677504
99518671430235219628894890102423325116913619626622
73267460800591547471830798392868535206946944540724
76841822524674417161514036427982273348055556214818
97142617910342598647204516893989422179826088076852
87783646182799346313767754307809363333018982642090
10848802521674670883215120185883543223812876952786
71329612474782464538636993009049310363619763878039
62184073572399794223406235393808339651327408011116
66627891981488087797941876876144230030984490851411
60661826293682836764744779239180335110989069790714
85786944089552990653640447425576083659976645795096
66024396409905389607120198219976047599490197230297
64913982680032973156037120041377903785566085089252
16730939319872750275468906903707539413042652315011
94809377245048795150954100921645863754710598436791
78639167021187492431995700641917969777599028300699
15368713711936614952811305876380278410754449733078
40789923115535562561142322423255033685442488917353
44889911501440648020369068063960672322193204149535
41503128880339536053299340368006977710650566631954
81234880673210146739058568557934581403627822703280
82616570773948327592232845941706525094512325230608
22918802058777319719839450180888072429661980811197
77158542502016545090413245809786882778948721859617
72107838435069186155435662884062257473692284509516
20849603980134001723930671666823555245252804609722
53503534226472524250874054075591789781264330331690
"""

problem18 = """
                     75
                    95 64
                  17 47 82
                 18 35 87 10
               20 04 82 47 65
             19 01 23 75 03 34
            88 02 77 73 07 63 67
           99 65 04 28 06 16 70 92
         41 41 26 56 83 40 80 70 33
       41 48 72 33 47 32 37 16 94 29
      53 71 44 65 25 43 91 52 97 51 14
    70 11 33 28 77 73 17 78 39 68 17 57
  91 71 52 38 17 14 91 43 58 50 27 29 48
 63 66 04 68 89 53 67 30 73 16 69 87 40 31
04 62 98 27 23 09 70 98 73 93 38 53 60 04 23
"""

########NEW FILE########
__FILENAME__ = problems
#!/usr/bin/python
import string

import data
from toolset import *

def problem1():
    """Add all the natural numbers below 1000 that are multiples of 3 or 5.""" 
    return sum(x for x in xrange(1, 1000) if x % 3 == 0 or x % 5 == 0)

def problem2():
    """Find the sum of all the even-valued terms in the Fibonacci < 4 million."""
    even_fibonacci = (x for x in fibonacci() if x % 2)
    return sum(takewhile(lambda x: x < 4e6, even_fibonacci))
  
def problem3():
    """Find the largest prime factor of a composite number."""
    return max(prime_factors(600851475143))

def problem4():
    """Find the largest palindrome made from the product of two 3-digit numbers."""
    # A brute-force solution is a bit slow, let's try to simplify it a little bit:
    # x*y = "abccda" = 100001a + 10010b + 1100c = 11 * (9091a + 910b + 100c)
    # So at least one of them must be multiple of 11. 
    candidates = (x*y for x in xrange(110, 1000, 11) for y in xrange(x, 1000))
    return max(x for x in candidates if is_palindromic(x))

def problem5():
    """What is the smallest positive number that is evenly divisible by all of 
    the numbers from 1 to 20?."""
    return reduce(least_common_multiple, range(1, 20+1))

def problem6():
    """Find the difference between the sum of the squares of the first one 
    hundred natural numbers and the square of the sum."""
    sum_of_squares = sum(x**2 for x in xrange(1, 100+1))
    square_of_sums = sum(xrange(1, 100+1))**2
    return square_of_sums - sum_of_squares

def problem7():
    """What is the 10001st prime number?."""
    return index(10001-1, get_primes())
  
def problem8():
    """Find the greatest product of five consecutive digits in the 1000-digit number"""
    digits = (int(c) for c in "".join(data.problem8.strip().splitlines()))
    return max(product(nums) for nums in groups(digits, 5, 1))
  
def problem9():
    """There exists exactly one Pythagorean triplet for which a + b + c = 1000.
    Find the product abc."""
    triplets = ((a, b, 1000-a-b) for a in xrange(1, 999) for b in xrange(a+1, 999))
    return first(a*b*c for (a, b, c) in triplets if a**2 + b**2 == c**2)
  
def problem10():
    """Find the sum of all the primes below two million."""
    return sum(takewhile(lambda x: x<2e6, get_primes()))

def problem11():
    """What is the greatest product of four adjacent numbers in any direction 
    (up, down, left, right, or diagonally) in the 20x20 grid?"""
    def grid_get(grid, nr, nc, sr, sc):
        """Return cell for coordinate (nr, nc) is a grid of size (sr, sc).""" 
        return (grid[nr][nc] if 0 <= nr < sr and 0 <= nc < sc else 0)
    grid = [map(int, line.split()) for line in data.problem11.strip().splitlines()]
    # For each cell, get 4 groups in directions E, S, SE and SW
    diffs = [(0, +1), (+1, 0), (+1, +1), (+1, -1)]
    sr, sc = len(grid), len(grid[0])
    return max(product(grid_get(grid, nr+i*dr, nc+i*dc, sr, sc) for i in range(4))
        for nr in range(sr) for nc in range(sc) for (dr, dc) in diffs)
        
def problem12():
    """What is the value of the first triangle number to have over five 
    hundred divisors?"""
    triangle_numbers = (triangle(n) for n in count(1))
    return first(tn for tn in triangle_numbers if ilen(divisors(tn)) > 500)

def problem13():
    """Work out the first ten digits of the sum of the following one-hundred 
    50-digit numbers."""
    numbers = (int(x) for x in data.problem13.strip().splitlines())
    return int(str(sum(numbers))[:10])

def problem14():
    """The following iterative sequence is defined for the set of positive 
    integers: n -> n/2 (n is even), n -> 3n + 1 (n is odd). Which starting 
    number, under one million, produces the longest chain?"""
    def collatz_function(n):        
        return ((3*n + 1) if (n % 2) else (n/2))
    @memoize
    def collatz_series_length(n):
        return (1 + collatz_series_length(collatz_function(n)) if n>1 else 0)
    return max(xrange(1, int(1e6)), key=collatz_series_length)

def problem15():
    """How many routes are there through a 20x20 grid?"""
    # To reach the bottom-right corner in a grid of size n we need to move n times
    # down (D) and n times right (R), in any order. So we can just see the 
    # problem as how to put n D's in a 2*n array (a simple permutation),
    # and fill the holes with R's -> permutations(2n, n) = (2n)!/(n!n!) = (2n)!/2n! 
    #   
    # More generically, this is also a permutation of a multiset
    # which has ntotal!/(n1!*n2!*...*nk!) permutations
    # In this problem the multiset is {n.D, n.R}, so (2n)!/(n!n!) = (2n)!/2n!
    n = 20
    return factorial(2*n) / (factorial(n)**2)

def problem16():
    """What is the sum of the digits of the number 2^1000?"""
    return sum(digits_from_num(2**1000))

def problem17():
    """If all the numbers from 1 to 1000 (one thousand) inclusive were written 
    out in words, how many letters would be used?"""
    strings = (get_cardinal_name(n) for n in xrange(1, 1000+1))
    return ilen(c for c in flatten(strings) if c.isalpha())

def problem18():
    """Find the maximum total from top to bottom of the triangle below:"""
    # The note that go with the problem warns that number 67 presents the same
    # challenge but much bigger, where it won't be possible to solve it using 
    # simple brute force. But let's use brute-force here and we'll use the 
    # head later. We test all routes from the top of the triangle. We will find 
    # out, however, that this brute-force solution is much more complicated to 
    # implement (and to understand) than the elegant one.
    def get_numbers(rows):
        """Return groups of "columns" numbers, following all possible ways."""
        for moves in cartesian_product([0, +1], repeat=len(rows)-1):
            indexes = ireduce(operator.add, moves, 0)
            yield (row[index] for (row, index) in izip(rows, indexes))
    rows = [map(int, line.split()) for line in data.problem18.strip().splitlines()]     
    return max(sum(numbers) for numbers in get_numbers(rows))

def problem19():
    """How many Sundays fell on the first of the month during the twentieth 
    century (1 Jan 1901 to 31 Dec 2000)?"""
    def is_leap_year(year):
        return (year%4 == 0 and (year%100 != 0 or year%400 == 0))
    def get_days_for_month(year, month):
        days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        return days[month-1] + (1 if (month == 2 and is_leap_year(year)) else 0)
    years_months = ((year, month) for year in xrange(1901, 2001) for month in xrange(1, 12+1))
    # Skip the last month (otherwise we would be checking for 1 Jan 2001)
    days = (get_days_for_month(y, m) for (y, m) in years_months if (y, m) != (2000, 12))    
    # Let's index Monday with 0 and Sunday with 6. 1 Jan 1901 was a Tuesday (1)
    weekday_of_first_day_of_months = ireduce(lambda wd, d: (wd+d) % 7, days, 1)
    return sum(1 for weekday in weekday_of_first_day_of_months if weekday == 6)

def problem20():
    """Find the sum of the digits in the number 100!"""
    return sum(digits_from_num(factorial(100)))

def problem21():
    """Evaluate the sum of all the amicable numbers under 10000."""
    sums = dict((n, sum(proper_divisors(n))) for n in xrange(1, 10000))
    return sum(a for (a, b) in sums.iteritems() if a != b and sums.get(b, 0) == a)

def problem22():
    """What is the total of all the name scores in the file?"""
    contents = data.openfile("names.txt").read()
    names = sorted(name.strip('"') for name in contents.split(","))
    dictionary = dict((c, n) for (n, c) in enumerate(string.ascii_uppercase, 1))
    return sum(i*sum(dictionary[c] for c in name) for (i, name) in enumerate(names, 1))

def problem23():
    """Find the sum of all the positive integers which cannot be written as 
    the sum of two abundant numbers."""
    abundants = set(x for x in xrange(1, 28123+1) if is_perfect(x) == 1)
    return sum(x for x in xrange(1, 28123+1) if not any((x-a in abundants) for a in abundants))

def problem24():
    """What is the millionth lexicographic permutation of the digits 
    0, 1, 2, 3, 4, 5, 6, 7, 8 and 9?"""
    return num_from_digits(index(int(1e6)-1, permutations(range(10), 10)))

def problem25():
    """What is the first term in the Fibonacci sequence to contain 1000 digits?"""
    # See relation between Fibanacci and the golden-ratio for a non brute-force solution
    return first(idx for (idx, x) in enumerate(fibonacci(), 1) if x >= 10**999)

def problem26():
    """Find the value of d < 1000 for which 1/d contains the longest recurring 
    cycle in its decimal fraction part."""
    def division(numerator, denominator):
        """Return (quotient, (decimals, cycle_length)) for numerator / denomominator."""
        def recursive(numerator, denominator, quotients, remainders):
            q, r = divmod(numerator, denominator)
            if r == 0:
                return (quotients + [q], 0)
            elif r in remainders:
                return (quotients, len(remainders) - remainders.index(r))
            else:       
                return recursive(10*r, denominator, quotients + [q], remainders + [r])
        decimals = recursive(10*(numerator % denominator), denominator, [], [])            
        return (numerator/denominator, decimals)
    # A smarter (and much faster) solution: countdown from 1000 getting cycles' 
    # length, and break when a denominator is lower the the current maximum 
    # length (since a cycle cannot be larger than the denominator itself).
    return max(xrange(2, 1000), key=lambda d: division(1, d)[1][1])

def problem27():
    """Find the product of the coefficients, a and b, for the quadratic 
    expression that produces the maximum number of primes for consecutive
    values of n, starting with n = 0."""
    def function(n, a, b):
        return n**2 + a*n + b
    def primes_for_a_b(a_b):
        return takewhile(is_prime, (function(n, *a_b) for n in count(0)))
    # b must be prime so n=0 yields a prime (b itself)
    b_candidates = list(x for x in xrange(1000) if is_prime(x))
    candidates = ((a, b) for a in xrange(-1000, 1000) for b in b_candidates)    
    return product(max(candidates, key=compose(ilen, primes_for_a_b)))

def problem28():
    """What is the sum of the numbers on the diagonals in a 1001 by 1001 spiral 
    formed in the same way?"""
    return 1 + sum(4*(n - 2)**2 + 10*(n - 1) for n in xrange(3, 1001+1, 2)) 
  
def problem29():
    """How many distinct terms are in the sequence generated by a**b for 
    2 <= a <= 100 and 2 <= b <= 100?"""
    return ilen(unique(a**b for a in xrange(2, 100+1) for b in xrange(2, 100+1)))
  
def problem30():
    """Find the sum of all the numbers that can be written as the sum of fifth 
    powers of their digits."""
    candidates = xrange(2, 6*(9**5))
    return sum(n for n in candidates if sum(x**5 for x in digits_from_num(n)) == n)

def problem31():
    """How many different ways can 2 pounds be made using any number of coins?"""
    def get_weights(units, remaining):
        """Return weights that sum 'remaining'. Pass units in descending order.  
        get_weigths([4,2,1], 5) -> (0,0,5), (0,1,3), (0,2,1), (1,0,1)"""   
        if len(units) == 1 and remaining % units[0] == 0:
            # Make it generic, do not assume that last unit is 1
            yield (remaining/units[0],)
        elif units:
            for weight in xrange(0, remaining + 1, units[0]):
                for other_weights in get_weights(units[1:], remaining - weight):
                   yield (weight/units[0],) + other_weights
    coins = [1, 2, 5, 10, 20, 50, 100, 200]
    return ilen(get_weights(sorted(coins, reverse=True), 200))

def problem32():
    """Find the sum of all products whose multiplicand/multiplier/product 
    identity can be written as a 1 through 9 pandigital"""
    def get_permutation(ndigits):
        return ((num_from_digits(ds), list(ds)) for ds in permutations(range(1, 10), ndigits))
    def get_multiplicands(ndigits1, ndigits2):
        return cartesian_product(get_permutation(ndigits1), get_permutation(ndigits2))
    # We have two cases for A * B = C: 'a * bcde = fghi' and 'ab * cde = fghi' 
    # Also, since C has always 4 digits, 1e3 <= A*B < 1e4
    candidates = chain(get_multiplicands(1, 4), get_multiplicands(2, 3))
    return sum(unique(a*b for ((a, adigits), (b, bdigits)) in candidates 
        if a*b < 1e4 and is_pandigital(adigits + bdigits + digits_from_num(a*b))))
        
def problem33():
    """There are exactly four non-trivial examples of this type of fraction, 
    less than one in value, and containing two digits in the numerator and 
    denominator. If the product of these four fractions is given in its lowest 
    common terms, find the value of the denominator."""
    def reduce_fraction(num, denom):
        gcd = greatest_common_divisor(num, denom)
        return (num / gcd, denom / gcd)
    def is_curious(numerator, denominator):
        if numerator == denominator or numerator % 10 == 0 or denominator % 10 == 0:
            return False
        # numerator / denominator = ab / cd
        (a, b), (c, d) = map(digits_from_num, [numerator, denominator])
        reduced = reduce_fraction(numerator, denominator)
        return (b == c and reduce_fraction(a, d) == reduced or 
                a == d and reduce_fraction(b, c) == reduced) 
    curious_fractions = ((num, denom) for num in xrange(10, 100) 
        for denom in xrange(num+1, 100) if is_curious(num, denom))
    numerator, denominator = map(product, zip(*curious_fractions))
    return reduce_fraction(numerator, denominator)[1]

def problem34():
    """Find the sum of all numbers which are equal to the sum of the factorial 
    of their digits."""
    # Cache digits from 0 to 9 to speed it up a little bit
    dfactorials = dict((x, factorial(x)) for x in xrange(10))
    
    # Upper bound: ndigits*9! < 10^ndigits -> upper_bound = ndigits*9!    
    # That makes 7*9! = 2540160. That's quite a number, so it will be slow.
    #
    # A faster alternative: get combinations with repetition of [0!..9!] in 
    # groups of N (1..7), and check the sum value. Note that the upper bound 
    # condition is in this case harder to apply.
    upper_bound = first(n*dfactorials[9] for n in count(1) if n*dfactorials[9] < 10**n)
    return sum(x for x in xrange(3, upper_bound) 
        if x == sum(dfactorials[d] for d in digits_from_num_fast(x)))
        
def problem35():
    """How many circular primes are there below one million?"""
    def is_circular_prime(digits):
        return all(is_prime(num_from_digits(digits[r:] + digits[:r])) 
            for r in xrange(len(digits)))
    # We will use only 4 digits (1, 3, 7, and 9) to generate candidates, so we 
    # must consider the four one-digit primes separately.
    circular_primes = (num_from_digits(ds) for n in xrange(2, 6+1) 
        for ds in cartesian_product([1, 3, 7, 9], repeat=n) if is_circular_prime(ds))
    return ilen(chain([2, 3, 5, 7], circular_primes))

def problem36():
    """Find the sum of all numbers, less than one million, which are 
    palindromic in base 10 and base 2."""
    # Apply a basic constraint: a binary number starts with 1, and to be 
    # palindromic it must also end with 1, so candidates are odd numbers.
    return sum(x for x in xrange(1, int(1e6), 2) 
        if is_palindromic(x, base=10) and is_palindromic(x, base=2))
        
def problem37():
    """Find the sum of the only eleven primes that are both truncatable from 
    left to right and right to left."""
    def truncatable_get_primes():
        for ndigits in count(2):
            digit_groups = [[2, 3, 5, 7]] + [[1, 3, 7, 9]]*(ndigits-2) + [[3, 7]]
            for ds in cartesian_product(*digit_groups):
                x = num_from_digits(ds)
                if is_prime(x) and all(is_prime(num_from_digits(ds[n:])) and
                        is_prime(num_from_digits(ds[:-n])) for n in range(1, len(ds))):
                    yield x
    return sum(take(11, truncatable_get_primes()))

def problem38():
    """What is the largest 1 to 9 pandigital 9-digit number that can be formed 
    as the concatenated product of an integer with (1,2, ... , n) where n > 1?"""
    def pandigital_concatenated_product(number):
        products = ireduce(operator.add, (digits_from_num(number*x) for x in count(1)))
        candidate_digits = first(ds for ds in products if len(ds) >= 9)
        if len(candidate_digits) == 9 and is_pandigital(candidate_digits):
            return num_from_digits(candidate_digits) 
    # 987654321 is the maximum (potential) pandigital, so 9876 is a reasonable upper bound
    return first(compact(pandigital_concatenated_product(n) for n in xrange(9876+1, 0, -1)))

def problem39():
    """if p is the perimeter of a right angle triangle with integral length 
    sides, {a,b,c}, for which value of p < 1000 is the number of solutions 
    maximized?"""
    def get_sides_for_perimeter(perimeter):
        sides = ((perimeter-b-c, b, c) for b in xrange(1, perimeter/2 + 1)
            for c in xrange(b, perimeter/2 + 1))
        return ((a, b, c) for (a, b, c) in sides if a**2 == b**2 + c**2)
    # Brute-force, check pythagorian triplets for a better solution
    return max(xrange(120, 1000), key=compose(ilen, get_sides_for_perimeter))

def problem40():
    """An irrational decimal fraction is created by concatenating the positive 
    integers: If dn represents the nth digit of the fractional part, find the 
    value of the following expression: d1 x d10 x d100 x d1000 x d10000 x 
    d100000 x d1000000"""
    def count_digits():
        """Like itertools.count, but returns digits instead. Starts at 1"""
        for nd in count(1):
            for digits in cartesian_product(*([range(1, 10)] + [range(10)]*(nd-1))):
                yield digits
    # We could get a formula for dn, but brute-force is fast enough
    indexes = set([1, 10, 100, 1000, 10000, 100000, 1000000])
    decimals = (d for (idx, d) in enumerate(flatten(count_digits()), 1) if idx in indexes)
    return product(take(len(indexes), decimals))

def problem41():
    """What is the largest n-digit pandigital prime that exists?"""
    # Use the disibility by 3 rule to filter some candidates: if the sum of 
    # digits is divisible by 3, so is the number (then it can't be prime). 
    maxdigits = first(x for x in range(9, 1, -1) if sum(range(1, x+1)) % 3)
    candidates = (num_from_digits(digits) for ndigits in range(maxdigits, 1, -1) 
        for digits in permutations(range(ndigits, 0, -1), ndigits))
    return first(x for x in candidates if is_prime(x))

def problem42():
    """Using words.txt (right click and 'Save Link/Target As...'), a 16K text 
    file containing nearly two-thousand common English words, how many are 
    triangle words?"""
    dictionary = dict((c, n) for (n, c) in enumerate(string.ascii_uppercase, 1))
    words = data.openfile("words.txt").read().replace('"', '').split(",")
    return ilen(word for word in words if is_triangle(sum(dictionary[c] for c in word)))

def problem43():
    """The number 1406357289 is a 0 to 9 pandigital number because it is made 
    up of each of the digits 0 to 9 in some order, but it also has a rather 
    interesting sub-string divisibility property. Let d1 be the 1st digit, d2 
    be the 2nd digit, and so on. In this way, we note the following: d2d3d4=406 
    is divisible by 2, d3d4d5=063 is divisible by 3, d4d5d6=635 is divisible 
    by 5, d5d6d7=357 is divisible by 7, d6d7d8=572 is divisible by 11, 
    d7d8d9=728 is divisible by 13, d8d9d10=289 is divisible by 17. 
    Find the sum of all 0 to 9 pandigital numbers with this property."""
    # Begin from the last 3-digits and backtrack recursively
    def get_numbers(divisors, candidates, acc_result=()):
        if divisors:
            for candidate in candidates:
                new_acc_result = candidate + acc_result
                if num_from_digits(new_acc_result[:3]) % divisors[0] == 0:
                    new_candidates = [(x,) for x in set(range(10)) - set(new_acc_result)]
                    for res in get_numbers(divisors[1:], new_candidates, new_acc_result):
                        yield res
        else:
            d1 = candidates[0]
            if d1: # d1 is the most significant digit, so it cannot be 0
                yield num_from_digits(d1 + acc_result)
    return sum(get_numbers([17, 13, 11, 7, 5, 3, 2], permutations(range(10), 3)))

def problem44():
    """Find the pair of pentagonal numbers, Pj and Pk, for which their sum 
    and difference is pentagonal and D = |Pk - Pj| is minimised; what is the 
    value of D?"""
    pairs = ((p1, p2) for (n1, p1) in ((n, pentagonal(n)) for n in count(0))
        for p2 in (pentagonal(n) for n in xrange(1, n1))
        if is_pentagonal(p1-p2) and is_pentagonal(p1+p2))        
    p1, p2 = first(pairs)
    return p1 - p2

def problem45():
    """It can be verified that T285 = P165 = H143 = 40755. Find the next 
    triangle number that is also pentagonal and hexagonal."""
    # Hexagonal numbers are also triangle, so we'll check only whether they are pentagonal
    hexagonal_candidates = (hexagonal(x) for x in count(143+1))
    return first(x for x in hexagonal_candidates if is_pentagonal(x))

def problem46():
    """What is the smallest odd composite that cannot be written as the sum 
    of a prime and twice a square?"""
    # primes will be iterated over and over and incremently, so better use a cached generator 
    primes = persistent(get_primes())
    def satisfies_conjecture(x):
        test_primes = takewhile(lambda p: p <  x, primes)
        return any(is_integer(sqrt((x - prime) / 2)) for prime in test_primes)
    odd_composites = (x for x in take_every(2, count(3)) if not is_prime(x))
    return first(x for x in odd_composites if not satisfies_conjecture(x))

def problem47():
    """Find the first four consecutive integers to have four distinct primes 
    factors. What is the first of these numbers?"""
    grouped_by_4factors = groupby(count(1), lambda x: len(set(prime_factors(x))) == 4)
    matching_groups = (list(group) for (match, group) in grouped_by_4factors if match)
    return first(grouplst[0] for grouplst in matching_groups if len(grouplst) == 4)

def problem48():
    """Find the last ten digits of the series, 1^1 + 2^2 + 3^3 + ... + 1000^1000"""
    return sum(x**x for x in xrange(1, 1000+1)) % 10**10

def problem49():
    """The arithmetic sequence, 1487, 4817, 8147, in which each of the terms 
    increases by 3330, is unusual in two ways: (i) each of the three terms are
    prime, and, (ii) each of the 4-digit numbers are permutations of one 
    another. There are no arithmetic sequences made up of three 1-, 2-, or 
    3-digit primes, exhibiting this property, but there is one other 4-digit 
    increasing sequence. What 12-digit number do you form by concatenating the 
    three terms in this sequence?"""
    def ds(n):
        return set(digits_from_num(n))
    def get_triplets(primes):
        for x1 in sorted(primes):
            for d in xrange(2, (10000-x1)/2 + 1, 2):
                x2 = x1 + d
                x3 = x1 + 2*d
                if x2 in primes and x3 in primes and ds(x1) == ds(x2) == ds(x3):
                    yield (x1, x2, x3)
    primes = set(takewhile(lambda x: x < 10000, get_primes(1000)))
    solution = index(1, get_triplets(primes))
    return num_from_digits(flatten(digits_from_num(x) for x in solution))

def problem50():
    """Which prime, below one-million, can be written as the sum of the most 
    consecutive primes?"""
    def get_max_length(primes, n, max_length=0, acc=None):
        if sum(take(max_length, drop(n, primes))) >= 1e6:
            return acc
        accsums = takewhile(lambda acc: acc<1e6, accsum(drop(n, primes)))
        new_max_length, new_acc = max((idx, acc) for (idx, acc) in 
            enumerate(accsums) if is_prime(acc))
        if new_max_length > max_length:
            return get_max_length(primes, n+1, new_max_length, new_acc)
        else:
            return get_max_length(primes, n+1, max_length, acc)
    primes = persistent(get_primes())
    return get_max_length(primes, 0)

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/python
"""
Run Project Euler problems in functional-programming style.

    $ wget http://projecteuler-solutions.googlecode.com/svn/trunk/Solutions.txt
    
    $ python run.py --solutions-file Solutions.txt 
    1: 233168 (ok) in 0.0002 seconds
    2: 4613732 (ok) in 0.0001 seconds
    ...

    $ python run.py --solutions-file Solutions.txt 1 5 9 
    1: 233168 (ok) in 0.0002 seconds
    5: 232792560 (ok) in 0.0000 seconds
    9: 31875000 (ok) in 0.1019 seconds

Author: Arnau Sanchez <tokland@gmail.com>
Website: http://github.com/tokland/pyeuler
"""
import optparse
import inspect
import time
import sys
import re

import problems

def run_problem(number, function, solutions=None):
    """Run a problem and return boolean state (None if no solution available)."""
    docstring = inspect.getdoc(function)
    itime = time.time()
    result = function()
    elapsed = time.time() - itime
    if solutions:
        solution = solutions[number]
        status = ("ok" if result == solution else 
            "FAIL: expected solution is %s" % solution)
        print "%d: %s (%s) in %0.3f seconds" % (number, result, status, elapsed)
        return (result == solution)
    else:
        print "%d: %s in %0.3f seconds" % (number, result, elapsed)

def parse_solutions(lines, format="^(?P<num>\d+)\.\s+(?P<solution>\S+)$"):
    """Yield pairs (problem_number, solution) parsed from lines."""
    re_format = re.compile(format)
    for line in lines:
        match = re_format.match(line.rstrip())
        if match:
            num, solution = int(match.group("num")), match.group("solution")
            solution2 = (int(solution) if re.match("[\d-]+$", solution) else solution)
            yield num, solution2 

def main(args):
    """Run Project Euler problems."""
    usage = """%prog [OPTIONS] [N1 [N2 ...]]

    Run solutions to Project Euler problems.""" 
    parser = optparse.OptionParser(usage)
    parser.add_option('-s', '--solutions-file', dest='solutions_file',
        default=None, metavar="FILE", type="string", help='Solutions file')
    options, args0 = parser.parse_args(args)
    
    solutions = (options.solutions_file and 
        dict(parse_solutions(open(options.solutions_file))))
    tosolve = map(int, args0)
    problem_functions = dict((int(re.match("problem(\d+)$", s).group(1)), fun) 
        for (s, fun) in inspect.getmembers(problems) if s.startswith("problem"))
        
    itime = time.time()
    statuses = [run_problem(num, fun, solutions) for (num, fun) in 
        sorted(problem_functions.iteritems()) if not tosolve or num in tosolve]
    elapsed = time.time() - itime
    ps = "problem" + ("" if len(statuses) == 1 else "s")    
    print "--- %d %s run (%d failed) in %0.3f seconds" % \
      (len(statuses), ps, statuses.count(False), elapsed) 
    return (0 if all(statuses) else 1)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = toolset
#!/usr/bin/python
import operator
from itertools import ifilter, islice, repeat, groupby
from itertools import count, imap, takewhile, tee, izip
from itertools import chain, starmap, cycle, dropwhile
from itertools import combinations, permutations, product as cartesian_product
from math import sqrt, log, log10, ceil

def take(n, iterable):
    """Take first n elements from iterable"""
    return islice(iterable, n)

def index(n, iterable):
    "Returns the nth item"
    return islice(iterable, n, n+1).next()

def first(iterable):
    """Take first element in the iterable"""
    return iterable.next()

def last(iterable):
    """Take last element in the iterable"""
    return reduce(lambda x, y: y, iterable)

def take_every(n, iterable):
    """Take an element from iterator every n elements"""
    return islice(iterable, 0, None, n)

def drop(n, iterable):
    """Drop n elements from iterable and return the rest"""
    return islice(iterable, n, None)

def ilen(it):
    """Return length exhausing an iterator"""
    return sum(1 for _ in it)

def product(nums):
    """Product of nums"""
    return reduce(operator.mul, nums, 1)

def irange(start_or_end, optional_end=None):
    """Return iterable that counts from start to end (both included)."""
    if optional_end is None:
        start, end = 0, start_or_end
    else:
        start, end = start_or_end, optional_end
    return take(max(end - start + 1, 0), count(start))

def flatten(lstlsts):
    """Flatten a list of lists"""
    return (b for a in lstlsts for b in a)

def compact(it):
    """Filter None values from iterator"""
    return ifilter(bool, it)

def groups(iterable, n, step):
    """Make groups of 'n' elements from the iterable advancing
    'step' elements on each iteration"""
    itlist = tee(iterable, n)
    onestepit = izip(*(starmap(drop, enumerate(itlist))))
    return take_every(step, onestepit)

def compose(f, g):
    """Compose two functions -> compose(f, g)(x) -> f(g(x))"""
    def _wrapper(*args, **kwargs):
        return f(g(*args, **kwargs))
    return _wrapper
  
def iterate(func, arg):
    """After Haskell's iterate: apply function repeatedly."""
    # not functional
    while 1:
        yield arg
        arg = func(arg)                

def accsum(it):
    """Yield accumulated sums of iterable: accsum(count(1)) -> 1,3,6,10,..."""
    return drop(1, ireduce(operator.add, it, 0))

def tails(seq):
    """Get tails of a sequence: tails([1,2,3]) -> [1,2,3], [2,3], [3], []."""
    for idx in xrange(len(seq)+1):
        yield seq[idx:]
     
def ireduce(func, iterable, init=None):
    """Like reduce() but using iterators (a.k.a scanl)"""
    # not functional
    if init is None:
        iterable = iter(iterable)
        curr = iterable.next()
    else:
        curr = init
        yield init
    for x in iterable:
        curr = func(curr, x)
        yield curr

def unique(it):
    """Return items from iterator (order preserved)"""
    # not functional, but fast
    seen = set()
    for x in it:
        if x not in seen:
            seen.add(x)
            yield x

def unique_functional(it):
    """Return items from iterator (order preserved)"""
    # functional but slow as hell. Just a proof-of-concept.
    steps = ireduce(lambda (last, seen), x: ((last, seen) if x in seen 
      else ([x], seen.union([x]))), it, ([], set()))
    return (m for (m, g) in groupby(flatten(last for (last, seen) in steps)))
        
def identity(x):
    """Do nothing and return the variable untouched"""
    return x

def occurrences(it, exchange=False):
    """Return dictionary with occurrences from iterable"""
    return reduce(lambda occur, x: dict(occur, **{x: occur.get(x, 0) + 1}), it, {})

def ncombinations(n, k):
    """Combinations of k elements from a group of n"""
    return cartesian_product(xrange(n-k+1, n+1)) / factorial(k)

def combinations_with_replacement(iterable, r):
    """combinations_with_replacement('ABC', 2) --> AA AB AC BB BC CC"""
    pool = tuple(iterable)
    n = len(pool)
    for indices in cartesian_product(range(n), repeat=r):
        if sorted(indices) == list(indices):
            yield tuple(pool[i] for i in indices)

# Common maths functions

def fibonacci():
    """Generate fibonnacci serie"""
    get_next = lambda (a, b), _: (b, a+b)
    return (b for (a, b) in ireduce(get_next, count(), (0, 1)))

def factorial(num):
    """Return factorial value of num (num!)"""
    return product(xrange(2, num+1))

def is_integer(x, epsilon=1e-6):
    """Return True if the float x "seems" an integer"""
    return (abs(round(x) - x) < epsilon)

def divisors(n):
    """Return all divisors of n: divisors(12) -> 1,2,3,6,12"""
    all_factors = [[f**p for p in range(fp+1)] for (f, fp) in factorize(n)]
    return (product(ns) for ns in cartesian_product(*all_factors))

def proper_divisors(n):
    """Return all divisors of n except n itself."""
    return (divisor for divisor in divisors(n) if divisor != n)

def is_prime(n):
    """Return True if n is a prime number (1 is not considered prime)."""
    if n < 3:
        return (n == 2)
    elif n % 2 == 0:
        return False
    elif any(((n % x) == 0) for x in xrange(3, int(sqrt(n))+1, 2)):
        return False
    return True

def get_primes(start=2, memoized=False):
    """Yield prime numbers from 'start'"""
    is_prime_fun = (memoize(is_prime) if memoized else is_prime)
    return ifilter(is_prime_fun, count(start))

def digits_from_num_fast(num):
    """Get digits from num in base 10 (fast implementation)"""
    return map(int, str(num))

def digits_from_num(num, base=10):
    """Get digits from num in base 'base'"""
    def recursive(num, base, current):
        if num < base:
            return current+[num]
        return recursive(num/base, base, current + [num%base])
    return list(reversed(recursive(num, base, [])))

def num_from_digits(digits, base=10):
    """Get digits from num in base 'base'"""
    return sum(x*(base**n) for (n, x) in enumerate(reversed(list(digits))) if x)

def is_palindromic(num, base=10):
    """Check if 'num' in base 'base' is a palindrome, that's it, if it can be
    read equally from left to right and right to left."""
    digitslst = digits_from_num(num, base)
    return digitslst == list(reversed(digitslst))

def prime_factors(num, start=2):
    """Return all prime factors (ordered) of num in a list"""
    candidates = xrange(start, int(sqrt(num)) + 1)
    factor = next((x for x in candidates if (num % x == 0)), None)
    return ([factor] + prime_factors(num / factor, factor) if factor else [num])

def factorize(num):
    """Factorize a number returning occurrences of its prime factors"""
    return ((factor, ilen(fs)) for (factor, fs) in groupby(prime_factors(num)))

def greatest_common_divisor(a, b):
    """Return greatest common divisor of a and b"""
    return (greatest_common_divisor(b, a % b) if b else a)

def least_common_multiple(a, b): 
    """Return least common multiples of a and b"""
    return (a * b) / greatest_common_divisor(a, b)

def triangle(x):
    """The nth triangle number is defined as the sum of [1,n] values."""
    return (x*(x+1))/2

def is_triangle(x):
    return is_integer((-1 + sqrt(1 + 8*x)) / 2)

def pentagonal(n):
    return n*(3*n - 1)/2

def is_pentagonal(n):
    return (n >= 1) and is_integer((1+sqrt(1+24*n))/6.0)

def hexagonal(n):
    return n*(2*n - 1)
       
def get_cardinal_name(num):
    """Get cardinal name for number (0 to 1 million)"""
    numbers = {
        0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
        6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
        11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
        15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
        19: "nineteen", 20: "twenty", 30: "thirty", 40: "forty",
        50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety",
      }
    def _get_tens(n):
      a, b = divmod(n, 10)
      return (numbers[n] if (n in numbers) else "%s-%s" % (numbers[10*a], numbers[b]))    
    def _get_hundreds(n):
      tens = n % 100
      hundreds = (n / 100) % 10
      return list(compact([
        hundreds > 0 and numbers[hundreds], 
        hundreds > 0 and "hundred", 
        hundreds > 0 and tens and "and", 
        (not hundreds or tens > 0) and _get_tens(tens),
      ]))

    # This needs some refactoring
    if not (0 <= num < 1e6):
      raise ValueError, "value not supported: %s" % num      
    thousands = (num / 1000) % 1000
    strings = compact([
      thousands and (_get_hundreds(thousands) + ["thousand"]),
      (num % 1000 or not thousands) and _get_hundreds(num % 1000),
    ])
    return " ".join(flatten(strings))

def is_perfect(num):
    """Return -1 if num is deficient, 0 if perfect, 1 if abundant"""
    return cmp(sum(proper_divisors(num)), num)

def number_of_digits(num, base=10):
    """Return number of digits of num (expressed in base 'base')"""
    return int(log(num)/log(base)) + 1

def is_pandigital(digits, through=range(1, 10)):
    """Return True if digits form a pandigital number"""
    return (sorted(digits) == through)

# Decorators

def memoize(f, maxcache=None, cache={}):
    """Decorator to keep a cache of input/output for a given function"""
    cachelen = [0]
    def g(*args, **kwargs):
        key = (f, tuple(args), frozenset(kwargs.items()))
        if maxcache is not None and cachelen[0] >= maxcache:
            return f(*args, **kwargs)
        if key not in cache:
            cache[key] = f(*args, **kwargs)
            cachelen[0] += 1
        return cache[key]
    return g

class tail_recursive(object):
    """Tail recursive decorator."""
    # Michele Simionato's version 
    CONTINUE = object() # sentinel

    def __init__(self, func):
        self.func = func
        self.firstcall = True

    def __call__(self, *args, **kwd):
        try:
            if self.firstcall: # start looping
                self.firstcall = False
                while True:
                    result = self.func(*args, **kwd)
                    if result is self.CONTINUE: # update arguments
                        args, kwd = self.argskwd
                    else: # last call
                        break
            else: # return the arguments of the tail call
                self.argskwd = args, kwd
                return self.CONTINUE
        except: # reset and re-raise
            self.firstcall = True
            raise
        else: # reset and exit
            self.firstcall = True
            return result
        
class persistent(object):
    def __init__(self, it):
        self.it = it
        
    def __getitem__(self, x):
        self.it, temp = tee(self.it)
        if type(x) is slice:
            return list(islice(temp, x.start, x.stop, x.step))
        else:
            return islice(temp, x, x+1).next()
        
    def __iter__(self):
        self.it, temp = tee(self.it)
        return temp

########NEW FILE########
__FILENAME__ = test_toolset
#!/usr/bin/python
import unittest

from pyeuler.toolset import *

class TestToolset(unittest.TestCase):
    def test_take(self):
        self.assertEqual(list(take(2, [1,2,3])), [1,2])
        self.assertEqual(list(take(0, [])), [])
        self.assertEqual(list(take(0, [1,2,3])), [])
        self.assertEqual(list(take(100, [1,2,3])), [1,2,3])
    
    def test_index(self):
        self.assertEqual(index(0, [1,2,3,4]), 1)
        self.assertEqual(index(3, [1,2,3,4]), 4)
        self.assertRaises(StopIteration, index, 0, [])
        self.assertRaises(StopIteration, index, 10, [1,2,3])

    def test_first(self):
        self.assertEqual(first(iter([1,2,3,4])), 1)
        self.assertRaises(StopIteration, first, iter([]))    

    def test_last(self):
        self.assertEqual(last(iter([1,2,3,4])), 4)
        self.assertRaises(TypeError, last, iter([]))    

    def test_take_every(self):
        self.assertEqual(list(take_every(1, [1,2,3,4])), [1,2,3,4])
        self.assertEqual(list(take_every(2, [1,2,3,4])), [1,3])
        self.assertEqual(list(take_every(10, [1,2,3,4])), [1])
        self.assertEqual(list(take_every(1, [])), [])

    def test_drop(self):
        self.assertEqual(list(drop(0, [1,2,3,4])), [1,2,3,4])
        self.assertEqual(list(drop(1, [1,2,3,4])), [2,3,4])
        self.assertEqual(list(drop(10, [1,2,3,4])), [])

    def test_ilen(self):
        self.assertEqual(ilen([]), 0)
        self.assertEqual(ilen([1, 2, 3]), 3)
        self.assertEqual(ilen(iter([1, 2, 3])), 3)
        
    def test_product(self):
        self.assertEqual(product([]), 1)
        self.assertEqual(product([2, 3]), 6)

    def test_flatten(self):
        self.assertEqual(flatten([]), [])
        self.assertEqual(flatten([[1,2,3], [4,5,6]]), [1,2,3,4,5,6])
        self.assertEqual(flatten([[1,2,3], [4,[5,6]]]), [1,2,3,4,[5,6]])

    def test_compact(self):
        self.assertEqual(list(compact([0, 1, "", None, [], (), "hello"])), [1, "hello"])
                
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
