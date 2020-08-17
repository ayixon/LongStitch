"""
Cut long reads and assign barcodes to the sub PE reads.
Usage: gunzip -c reads.fa.gz | python long-to-linked.py -l frag_len | gzip > reads.cutlength.fa.gz

"""

from __future__ import print_function
import argparse
import sys

if sys.version_info[0] < 3:
    from string import maketrans
    complements_trans = maketrans('ACGTacgt','TGCATGCA')
else:
    complements_trans = str.maketrans('ACGTacgt','TGCATGCA')


def reverse_complement(seq):
    return seq[::-1].translate(complements_trans)


# From https://github.com/lh3/readfq
def readfq(fp): # this is a generator function
    last = None # this is a buffer keeping the last unprocessed line
    while True: # mimic closure; is it a bad idea?
        if not last: # the first record or a record following a fastq
            for l in fp: # search for the start of the next record
                if l[0] in '>@': # fasta/q header line
                    last = l[:-1] # save this line
                    break
        if not last: break
        name, seqs, last = last[1:].partition(" ")[0], [], None
        for l in fp: # read the sequence
            if l[0] in '@+>':
                last = l[:-1]
                break
            seqs.append(l[:-1])
        if not last or last[0] != '+': # this is a fasta record
            yield name, ''.join(seqs), None # yield a fasta record
            if not last: break
        else: # this is a fastq record
            seq, leng, seqs = ''.join(seqs), 0, []
            for l in fp: # read the quality
                seqs.append(l[:-1])
                leng += len(l) - 1
                if leng >= len(seq): # have read enough quality
                    last = None
                    yield name, seq, ''.join(seqs); # yield a fastq record
                    break
            if last: # reach EOF before reading enough quality
                yield name, seq, None # yield a fasta record instead
                break


def convert_long_to_linked(in_reads, read_len):
    bx = 0
    frag_len = 2 * read_len
    for name, seq, qual in readfq(in_reads):
        bx += 1
        current_id = name.strip() + "_f{} BX:Z:" + str(bx)
        seq = seq.strip()

        if len(seq) < frag_len:
            continue

        # Split ONT read into fragments of size frag_len
        read_frags = [seq[i:frag_len + i] for i in range(0, len(seq), frag_len)]

        f = 0
        for frag in read_frags:
            f += 1
            r1 = frag[:read_len]
            r2 = reverse_complement(frag[-read_len:])

            # Write R1 and R2
            print(">" + current_id.format(f) + "\n" + r1)            
            print(">" + current_id.format(f) + "\n" + r2)


def main():
    parser = argparse.ArgumentParser(description="Split long reads into pseudo-linked reads.")
    parser.add_argument("input", type=argparse.FileType('r'), default=sys.stdin, nargs='?')
    parser.add_argument("-l", "--length", type=int, help="Read length", required=True)

    args = parser.parse_args()
    in_reads = args.input
    read_len = args.length
    convert_long_to_linked(in_reads, read_len)


if __name__ == '__main__':
    main()
