
import argparse 
import csv
import json
import re
import sys



def is_good_run(run_num, good_run_lumi_sec_map):
	return (run_num in good_run_lumi_sec_map)

def is_good_lumi_section(run_num, lumi_sec, good_run_lumi_sec_map):
	if run_num not in good_run_lumi_sec_map:
		return False

	for (min_lumi_sec, max_lumi_sec) in good_run_lumi_sec_map[run_num]:
		if ( (lumi_sec >= min_lumi_sec) and (lumi_sec <= max_lumi_sec) ):
			return True

	return False

def get_lumi_range_intersection(run_num, min_lumi_sec, max_lumi_sec, good_run_lumi_sec_map):
	assert min_lumi_sec <= max_lumi_sec, "min_lumi_sec="+str(min_lumi_sec)+" is not <= max_lumi_sec="+str(max_lumi_sec)
	if run_num not in good_run_lumi_sec_map:
		return []

	intersections = []

	for (min_lumi_sec2, max_lumi_sec2) in good_run_lumi_sec_map[run_num]:
		potential_min = max(min_lumi_sec, min_lumi_sec2)
		potential_max = min(max_lumi_sec, max_lumi_sec2)
		if (potential_min <= potential_max):
			intersections += [(potential_min, potential_max)]

	return intersections

assert get_lumi_range_intersection(1234, 1, float('+Inf'), {1234: [(12, 42), (53, 64)]}) == [(12, 42), (53, 64)]



if __name__ == '__main__':

	# Set up argument parser
	parser = argparse.ArgumentParser(description='Finds run/lumi ranges over which trigger paths have fixed pre-scale')
	parser.add_argument('certDataJson', help='JSON file specifying certified lumi section ranges')
	parser.add_argument('triggerPrescaleFile', help='CSV-format files containing trigger prescale information')

	# Parse the arguments
	args = parser.parse_args()

	# Import data from files
	print "Importing data from input files ..."
	
	print "   Data cert JSON:", args.certDataJson
	with open(args.certDataJson) as json_file:
		json_data = json.load(json_file)
	cert_runs_lumi_sections = {int(k): v for k, v in json_data.iteritems()}
	del json_data

	print "   trigger prescale CSV file:", args.triggerPrescaleFile
	trigger_info_map = {}
	with open(args.triggerPrescaleFile) as trigger_prescale_file:
		csv_reader = csv.reader(trigger_prescale_file, delimiter=',')

		# Skip first two rows - headers
		# FIXME: Check that headers sufficiently match expectations
		csv_reader.next()
		csv_reader.next()

		for row in csv_reader:
			# FORMAT: run,cmsls,prescidx,totprescval,hltpath/prescval,logic,l1bit/prescval
			run_num = int(row[0])
			print "run_num:", run_num

			# Ignore lines for runs that don't appear in list of certified lumi sections
			if not is_good_run(run_num, cert_runs_lumi_sections):
				continue

			start_ls = int(row[1])
			prescale = int(row[3])
			hlt_path = re.match(r"([A-Za-z0-9_]+_v\d+)/\d+", row[4]).group(1)
			l1seed = (row[5],row[6])

			#print hlt_path, (run_num, start_ls, prescale, l1seed)
			if hlt_path in trigger_info_map:
				trigger_info_map[hlt_path] += [(run_num, start_ls, prescale, l1seed)]
			else:
				trigger_info_map[hlt_path] = [(run_num, start_ls, prescale, l1seed)]


	print
	print
	print "   >>>  PARSED TRIGGER INFO  <<<"
	minimal_trigger_info_map = {}
	for hlt_path in trigger_info_map:
		print hlt_path
		for prescale_info in trigger_info_map[hlt_path]:
			print "   ", prescale_info
		print "  ... proccessing ..."
		lumi_section_prescale_list = trigger_info_map[hlt_path]

		# Step 0: Sort prescale info list so that ordered in run number & lumi section
		lumi_section_prescale_list.sort(key=lambda x: (x[0],x[1]))


		# Step 1: Update LS info in list from just 'start LS' to ('start LS', 'end LS') tuple
		for i in range(len(lumi_section_prescale_list)):
			if i == (len(lumi_section_prescale_list) - 1):
				lumi_section_prescale_list[i] = lumi_section_prescale_list[i][:1] + ((lumi_section_prescale_list[i][1], float('+Inf')), ) + lumi_section_prescale_list[i][2:]
			else:
				# Make sure that list is ordered in (run section, lumi section)
				assert(lumi_section_prescale_list[i][0] <= lumi_section_prescale_list[i+1][0])
				if lumi_section_prescale_list[i][0] == lumi_section_prescale_list[i+1][0]:
					# Make sure that list is ordered in (run section, lumi section)
					assert(lumi_section_prescale_list[i][1] < lumi_section_prescale_list[i+1][1])

					lumi_section_prescale_list[i] = lumi_section_prescale_list[i][:1] + ((lumi_section_prescale_list[i][1], lumi_section_prescale_list[i+1][1]-1), ) + lumi_section_prescale_list[i][2:]
				else:
					lumi_section_prescale_list[i] = lumi_section_prescale_list[i][:1] + ((lumi_section_prescale_list[i][1], float('+Inf')), ) + lumi_section_prescale_list[i][2:]


		# Step 2: Add 'prescale = 0' entries for runs that appear in the 'good LS' list, but in which this trigger path was not defined
		runs_with_trigger_path_defined = set(x[0] for x in lumi_section_prescale_list)
		for cert_run_nr in sorted(cert_runs_lumi_sections.keys()):
			if cert_run_nr not in runs_with_trigger_path_defined:
				lumi_section_prescale_list += [(cert_run_nr, (0, float('+Inf')), 0, None)]

		lumi_section_prescale_list.sort(key=lambda x: (x[0],x[1]))

		# for prescale_info in lumi_section_prescale_list:
		# 	print "   ", prescale_info


		# Step 3: Remove entries in trigger prescale info list that have no overlap with 'good LS' list
		lumi_section_prescale_list = [item for item in lumi_section_prescale_list if len(get_lumi_range_intersection(item[0], item[1][0], item[1][1], cert_runs_lumi_sections)) != 0]


		# print "  ... becomes ..."
		# for prescale_info in lumi_section_prescale_list:
		# 	print "   ", prescale_info

		# Step 4: Aggregate runs and LS ranges that are continous, with constant prescales + seeds, within the 'good LS' list
		assert(len(lumi_section_prescale_list) > 0)
		minimal_lumi_section_prescale_list = []
		i, j = 0, 0
		while True:
#			print "i =", i, ", j =", j, "len(lumi_section_prescale_list) =", len(lumi_section_prescale_list)
			# (run_num, (start_ls, end_ls), prescale, l1seed)
			item_i = lumi_section_prescale_list[i]
			item_j = lumi_section_prescale_list[j]

			if (j == len(lumi_section_prescale_list)-1) or (item_j[2] != lumi_section_prescale_list[j+1][2]) or (item_j[3] != lumi_section_prescale_list[j+1][3]):
#				print "  Accumulated entries"
				minimal_lumi_section_prescale_list += [( (item_i[0], item_i[1][0]), (item_j[0], item_j[1][1]), item_i[2], item_i[3])]

				if (j == len(lumi_section_prescale_list)-1):
					break
				else:
					i = j + 1
					j = j + 1
			else:
				j = j + 1

		minimal_trigger_info_map[hlt_path] = minimal_lumi_section_prescale_list

		# print "  ... becomes ..."

		# for prescale_info in minimal_lumi_section_prescale_list:
		# 	print "   ", prescale_info


	print "   >>>  PARSED TRIGGER INFO  <<<"
	for hlt_path in sorted(minimal_trigger_info_map.keys()):
		print hlt_path
		for prescale_info in minimal_trigger_info_map[hlt_path]:
			if prescale_info[2] != 1:
				print "  xx ", prescale_info
			else:
				print "     ", prescale_info
		print "\n\n\n"

