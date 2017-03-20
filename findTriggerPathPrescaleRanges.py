
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


# Describes period with fixed prescale & L1 seed for given trigger path
class FixedTriggerPeriod:
	def __init__(self, hlt_path, start_run, start_ls, end_run, end_ls, prescale, l1seed):
		self.hlt_path = hlt_path
		self.start_run = start_run
		self.start_ls = start_ls
		self.end_run = end_run
		self.end_ls = end_ls
		self.prescale = prescale
		if l1seed is None:
			self.l1seed = l1seed
		else:
			l1seed_list = l1seed[1].split(' ')
			l1seed_list.sort()
			self.l1seed = (l1seed[0], ' '.join(l1seed_list))

	def __str__(self):
		return "run {0} ls {1:>4} - {2} ls {3:>4}".format(self.start_run, self.start_ls, self.end_run, self.end_ls) + " :  " + self.hlt_path + "  /{0:>5}".format(self.prescale) + "   " + str(self.l1seed)


assert FixedTriggerPeriod("hlt_a_path/vX", 12345, 42, 12346, 55, 42, ("OR", "L1_HTT280/1 L1_HTT220/3500 L1_HTT270/1 L1_HTT320/1 L1_HTT300/1 L1_HTT160/5250 L1_HTT200/0 L1_HTT255/1 L1_HTT240/1")).l1seed[1] == "L1_HTT160/5250 L1_HTT200/0 L1_HTT220/3500 L1_HTT240/1 L1_HTT255/1 L1_HTT270/1 L1_HTT280/1 L1_HTT300/1 L1_HTT320/1"

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
			# print "run_num:", run_num

			# Ignore lines for runs that don't appear in list of certified lumi sections
			if not is_good_run(run_num, cert_runs_lumi_sections):
				continue

			start_ls = int(row[1])
			prescale = int(row[3])
			hlt_path_unversioned = re.match(r"([A-Za-z0-9_]+)_v\d+/\d+", row[4]).group(1)
			hlt_path_full = re.match(r"([A-Za-z0-9_]+_v\d+)/\d+", row[4]).group(1)
			l1seed = (row[5],row[6])

			#print hlt_path, (run_num, start_ls, prescale, l1seed)
			if hlt_path_unversioned in trigger_info_map:
				trigger_info_map[hlt_path_unversioned].append( FixedTriggerPeriod(hlt_path_full, run_num, start_ls, run_num, None, prescale, l1seed) )
			else:
				trigger_info_map[hlt_path_unversioned] = [ FixedTriggerPeriod(hlt_path_full, run_num, start_ls, run_num, None, prescale, l1seed) ]

# FixedTriggerPeriod: __init__(self, hlt_path, start_run, start_ls, end_run, end_ls, prescale, l1seed)
	print
	print
	print "   >>>  PARSED TRIGGER INFO  <<<"
	minimal_trigger_info_map = {}
	for hlt_path in trigger_info_map:
		print hlt_path
		for prescale_info in trigger_info_map[hlt_path]:
			print "   ", prescale_info
		# print "  ... proccessing ..."
		lumi_section_prescale_list = trigger_info_map[hlt_path]

		# Step 0: Sort prescale info list so that ordered in run number & lumi section
		lumi_section_prescale_list.sort(key=lambda x: (x.start_run, x.start_ls))


		# Step 1: Update LS info in list from just 'start LS' to ('start LS', 'end LS') tuple
		for i in range(len(lumi_section_prescale_list)):
			assert lumi_section_prescale_list[i].start_run == lumi_section_prescale_list[i].end_run

			if i == (len(lumi_section_prescale_list) - 1):
				lumi_section_prescale_list[i].end_ls = float('+Inf')
			else:
				# Make sure that list is ordered in (run section, lumi section)
				assert(lumi_section_prescale_list[i].start_run <= lumi_section_prescale_list[i+1].start_run)
				if lumi_section_prescale_list[i].start_run == lumi_section_prescale_list[i+1].start_run:
					# Make sure that list is ordered in (run section, lumi section)
					assert(lumi_section_prescale_list[i].start_ls < lumi_section_prescale_list[i+1].start_ls)

					lumi_section_prescale_list[i].end_ls = lumi_section_prescale_list[i+1].start_ls - 1
				else:
					lumi_section_prescale_list[i].end_ls = float('+Inf')


		# Step 2: Add 'prescale = 0' entries for runs that appear in the 'good LS' list, but in which this trigger path was not defined
		runs_with_trigger_path_defined = set(x.start_run for x in lumi_section_prescale_list)
		for cert_run_nr in sorted(cert_runs_lumi_sections.keys()):
			if cert_run_nr not in runs_with_trigger_path_defined:
				lumi_section_prescale_list.append( FixedTriggerPeriod("null", cert_run_nr, 0, cert_run_nr, float('+Inf'), 0, None) )

		lumi_section_prescale_list.sort(key=lambda x: (x.start_run, x.start_ls))

		# for prescale_info in lumi_section_prescale_list:
		# 	print "   ", prescale_info


		# Step 3: Remove entries in trigger prescale info list that have no overlap with 'good LS' list
		lumi_section_prescale_list = [item for item in lumi_section_prescale_list if len(get_lumi_range_intersection(item.start_run, item.start_ls, item.end_ls, cert_runs_lumi_sections)) != 0]


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

			if (j == len(lumi_section_prescale_list)-1) or (item_i.hlt_path != item_j.hlt_path) or (item_j.prescale != lumi_section_prescale_list[j+1].prescale) or (item_j.l1seed != lumi_section_prescale_list[j+1].l1seed):
#				print "  Accumulated entries"
				minimal_lumi_section_prescale_list.append( FixedTriggerPeriod(item_i.hlt_path, item_i.start_run, item_i.start_ls, item_j.end_run, item_j.end_ls, item_i.prescale, item_i.l1seed) )

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
			if prescale_info.prescale != 1:
				print "  xx ", prescale_info
			else:
				print "     ", prescale_info
		print "\n\n\n"

