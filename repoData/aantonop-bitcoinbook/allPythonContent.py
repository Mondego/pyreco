__FILENAME__ = hash_example

# example of iterating a nonce in a hashing algorithm's input

import hashlib
    
text = "I am Satoshi Nakamoto"

for nonce in xrange(20):  # iterate nonce from 0 to 19
    input = text + str(nonce)  # add the nonce to the end of the text
    hash = hashlib.sha256(input).hexdigest() # calculate the SHA-256 hash of the input (text+nonce)
    print input, '=>',  hash # show the input and hash result
########NEW FILE########
__FILENAME__ = proof-of-work-example
#!/usr/bin/env python
# example of proof-of-work algorithm

import hashlib
import time

max_nonce = 2 ** 32 # 4 billion

def proof_of_work(header, difficulty_bits):
    
    target = 2 ** (256-difficulty_bits)
    
    for nonce in xrange(max_nonce):
        hash_result = hashlib.sha256(str(header)+str(nonce)).hexdigest()
        
        if long(hash_result, 16) < target:
            print "Success with nonce %d" % nonce
            print "Hash is %s" % hash_result
            return (hash_result,nonce)
            
    print "Failed after %d (max_nonce) tries" % nonce
    return nonce

    
if __name__ == '__main__':
    
    nonce = 0
    hash_result = ''
        
    for difficulty_bits in xrange(32):
        
        difficulty = 2 ** difficulty_bits
        print "Difficulty: %ld (%d bits)" % (difficulty, difficulty_bits)
    
        print "Starting search..."
        start_time = time.time()
        new_block = 'test block with transactions' + hash_result # make a new block which includes the hash from the previous block
        (hash_result, nonce) = proof_of_work(new_block, difficulty_bits) # find a nonce for the new block
        end_time = time.time()
        elapsed_time = end_time - start_time
        print "Elapsed Time: %.4f seconds" % elapsed_time
    
        if elapsed_time > 0:
            hash_power = float(long(nonce)/elapsed_time)
            print "Hashing Power: %ld hashes per second" % hash_power
    
    
    
########NEW FILE########
