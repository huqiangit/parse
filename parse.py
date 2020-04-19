#!/usr/bin/python

import os
import sys
import struct

sync_words = [
	{
		"words" : [0xf8, 0x72, 0x4e, 0x1f, 0x00, 0x0b],
		"div" : 1,
		"change_iec_endian" : 0,
        "change_payload_endian" : 0,
        "contain_iec_header" : 0
	},
	{
		"words" : [0xf8, 0x72, 0x4e, 0x1f, 0x04, 0x11],
		"div" : 1,
		"change_iec_endian" : 0,
        "change_payload_endian" : 0,
        "contain_iec_header" : 0
	},	
]

prev_match_index = -1

def is_match (buf_mode, buf_src):
	buf_src_len = len (buf_src)
	buf_mode_len = len (buf_mode)

	if (buf_src_len < 8):
		return -1

	for i in range (0, buf_mode_len):
		if (buf_src[i] != buf_mode[i]):
			return 0

	return 1

def find_match_word (sub_buf, sync_words):
	for n in range (0, len(sync_words)):
		res = is_match (sync_words[n]["words"], sub_buf)
		if (res == 0):
			continue
		elif (res == 1):
			return {
				"state" : 1,
				"table_index" : n
			}
		else:
			return {
				"state" : -1,
				"table_index" : -1
			}

	return {
		"state" : 0,
		"table_index" : -1
	}

def got_data (sub_buf, sync_words_table, table_index):
	data = {
		"buf" : [],
		"len" : 0,
		"skip" : 0
	}

	if ((sub_buf[6] * 256 + sub_buf[7]) % sync_words_table[table_index]["div"]) == 0:
		payload_len = (sub_buf[6] * 256 + sub_buf[7]) / sync_words_table[table_index]["div"]
		print ("payload len: ", payload_len)
		
		if (sync_words_table[table_index]["contain_iec_header"] == 1):
			data["buf"] = process_chang_endian (sub_buf[0:8], sync_words_table[table_index]["change_iec_endian"])
			data["buf"] += process_chang_endian (sub_buf[8:(8 + payload_len)], sync_words_table[table_index]["change_payload_endian"])
			data["len"] = 8 + payload_len
			data["skip"] = 8 + payload_len
		else:
			data["buf"] = process_chang_endian (sub_buf[8:(8 + payload_len)], sync_words_table[table_index]["change_payload_endian"])
			data["len"] = payload_len
			data["skip"] = 8 + payload_len

		if len(sub_buf) < (8 + payload_len):
			print ("warning data not enough at end")

	else:
		data["buf"] = []
		data["len"] = 0
		data["skip"] = 0
		print ("warning payload_len mod not zero")

	return data

def get_output (buf, sync_words):
	data_set = []
	global prev_match_index


	off = 0
	while (off < len (buf)):
		tmp_buf = buf[off:]
		res = find_match_word (tmp_buf, sync_words)

		if (res["state"] == -1):
			print ("      end: %d %s", off)#, print_buf(tmp_buf))
			return data_set
		elif (res["state"] == 0):
			#print ("unmatched: %d %s", off)#, print_buf(tmp_buf))
			off += 1
		# // == 1
		else:
			print ("\n  ===> matched: off %d kink %s" % (off, res["table_index"]))#, print_buf(tmp_buf))

			if (prev_match_index == -1):
				prev_match_index = res["table_index"]

				data_res = got_data (tmp_buf, sync_words, prev_match_index)

				tmp = {
					"buff" : data_res["buf"],
					"len" : data_res["len"],
					"table_index" : prev_match_index
				}
				data_set.append (tmp)
				print ("-> cur off", off, "skip",  data_res["skip"], "after off", off + data_res["skip"])
				off += data_res["skip"]
			else:
				if (prev_match_index == res["table_index"]):
					data_res = got_data (tmp_buf, sync_words, prev_match_index)
					bb = data_set[-1]["buff"]

					data_set[-1]["buff"] = bb + data_res["buf"]
					data_set[-1]["len"] += data_res["len"]

					print ("-> cur off", off, "skip",  data_res["skip"], "after off", off + data_res["skip"])
					off += data_res["skip"]
				else:
					prev_match_index = res["table_index"]
					data_res = got_data(tmp_buf, sync_words, prev_match_index)

					tmp = {
						"buff" : data_res["buf"],
						"len" : data_res["len"],
						"table_index" : prev_match_index
					}

					data_set.append(tmp)

					print ("-> cur off", off, "skip",  data_res["skip"], "after off", off + data_res["skip"])
					off += data_res["skip"]
	
	return data_set


def print_buf (buf):
	str = ""
	for i in range (0, len(buf)):
		str += "%02x" % buf[i] + " "
	
	return str;

def binary_save (path, buf):
	file_out_hd = open (path, mode='wb')

	for i in range (0, len(buf)):
		file_out_hd.write (struct.pack('B', buf[i]))

	file_out_hd.close ()

def binary_load (path):
	file_in_size = os.path.getsize(path)
	file_in_hd = open(path, mode='rb')
	data_array = struct.unpack('{}B'.format(file_in_size), file_in_hd.read())
	
	data = []
	for i in range (0, len(data_array)):
		data.append(data_array[i])

	print ("load: %d" % len(data) + "bytes")
	file_in_hd.close()
	return data

	
def process_chang_endian (buf, need_change):
	new_buf = []

	if need_change == 1:
		for i in range (0, len(buf), 2):
			if i == (len(buf)-1):
				new_buf.append(0)
				new_buf.append(buf[i])
			else:
				new_buf.append(buf[i+1])
				new_buf.append(buf[i+0])
		return new_buf
	else:
		return buf




if __name__ == '__main__':

	file_in_data = binary_load (sys.argv[1])
	#print (print_buf(file_in_data))

	d = get_output (file_in_data, sync_words)
	#print (print_buf(d[-1]["buff"]))

	binary_save ("out.dat", d[-1]["buff"])





