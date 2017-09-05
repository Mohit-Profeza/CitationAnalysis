import requests, operator
import xml.etree.ElementTree as ET
import sys, json, os, urllib, nltk, re
from bs4 import BeautifulSoup

class ParsePMC:
	def __init__(self, pid):
		self.pid = pid
		self.stopwords = set(nltk.corpus.stopwords.words('english'))
		return

	def get_metadata(self, pid):
		url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pmc&id=%s&retmode=json&tool=my_tool&email=my_email@example.com"%pid
                response = requests.get(url).json()
		doi = filter(lambda x: x['idtype'] == 'doi', response['result'][pid]['articleids']) \
			if pid in response['result'] and 'articleids' in response['result'][pid] else None
		if doi and len(doi):
			doi = doi[0]['value']
		if not doi:
			print "NO DOI FOUND", response
			error = {'error': "DOI Not Found : %s (%s) - (%s)"%(response['result'][pid]['fulljournalname'] \
				if 'fulljournalname' in response['result'][pid] else "",
				response['result'][pid]['title'] if 'title' in response['result'][pid] else "",
				response['result'][pid]['pubdate'] if 'pubdate' in response['result'][pid] else ""),
				'response': response}
			return [None, None, error]
		doi_url = "https://api.oadoi.org/v2/%s?email=test@example.com"%doi
		doi_response = requests.get(doi_url).json()
		if not 'best_oa_location' in doi_response or not doi_response['best_oa_location']:
			print doi_response
			error = {'error': "OA URL Not Found : %s, %s (%s) - %s \n"%(doi_response['journal_name'] \
				if 'journal_name' in doi_response else "",
				doi_response['publisher'] if 'publisher' in doi_response else "",
				doi_response['title'] if 'title' in doi_response else "",
				doi_response['updated'] if 'updated' in doi_response else ""),
				'doi_response': doi_response,
				'response': response}
			return [None, None, error]
		print doi_response
		doi_response_data = json.dumps(doi_response)
		doi_oa_url = doi_response['best_oa_location']['url'] if 'url' in doi_response['best_oa_location'] else ""
		return [doi_oa_url, doi_response_data, None]

	def get_citations(self):
		url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&linkname=pubmed_pmc_refs&id=%s"%self.pid
		response = requests.get(url)
		tree = ET.fromstring(response.content)
		url_save_file_list = []
		for i in tree.getiterator():
			if i.tag == 'Id':
				if 1:#try:
					doi_oa_url, response_data, error = self.get_metadata(i.text)
					print doi_oa_url
					if not error:
						self.citationdump(str(self.pid), response_data)
						url_save_file_list.append([self.pid, doi_oa_url])
					else:
						self.citationdump("error_%s"%str(self.pid), json.dumps(error))
				#except:
				#	print sys.exc_info()
		return


	def citationdump(self, filename, content):
		print content
		f = open("master_%s.txt"%filename, 'a')
		f.write("%s\n"%content)
		f.close()
		return 

	def analyze_citation(self):
		error_file = open("master_error_%s.txt"%self.pid, 'r')
		doi_url_file = open("master_%s.txt"%self.pid, 'r')
		error_data = {'no_doi': 0, 'no_url': 0}
		for i in error_file.readlines():
			line_data = json.loads(i)
			if 'DOI Not Found' in line_data['error']:
				error_data['no_doi'] += 1
			if 'OA URL Not Found' in line_data['error']:
				error_data['no_url'] += 1
		print "Creating Local Text Copies of Paper"
		for i in doi_url_file.readlines():
			doi_url_data = json.loads(i)
			doi_url = doi_url_data['best_oa_location']['url']
			doi_file_name = doi_url_data['doi'].replace("/", "_")
			if not os.path.exists("%s.txt"%doi_file_name):
				print "Creating File for %s"%doi_file_name
				urllib.urlretrieve(doi_url, "%s.txt"%doi_file_name)
			else:
				print "File Found : %s.txt"%doi_file_name
			self.find_citation("%s.txt"%doi_file_name)
		print "Analyzing Files"
		return

	def find_citation(self, doi_file_name):
		self.pid_title = "The common feature of leukemia-associated IDH1 and IDH2 mutations is a neomorphic enzyme activity converting alpha-ketoglutarate to 2-hydroxyglutarate"
		self.pid_author = "Ward PS, Patel J, Wise DR, Abdel-Wahab O, Bennett BD, Coller HA, Cross JR, Fantin VR, Hedvat CV, Perl AE, Rabinowitz JD, Carroll M, Su SM, Sharp KA, Levine RL, Thompson CB."
		pid_author = self.pid_author.split(", ")
		doi_file = open(doi_file_name, 'r')
		soup = BeautifulSoup(doi_file.read())
		file_content = soup.get_text()
		self.file_content = file_content
		if self.pid_title in file_content:
			# Reference Index of Paper Title
			title_occ = list(self.find_all(file_content, self.pid_title))
			print "Title Index : ", title_occ
			numeric_citation = []
			for i in title_occ:
				print "Index (%s) : "%i, file_content[i - 20: i + 20]
				# Check for numeric citation
				title_numeric_citation = [int(s) for s in file_content[i - 4: i].split() if s.isdigit()]
				if len(title_numeric_citation):
					print "# Numeric Citation of Title : ", title_numeric_citation
					numeric_citation.append(title_numeric_citation)
			self.author_ref_index = []
			print "========== Found Reference Title =========="
			# Finding Author Citation in text
			for i in pid_author:
				# Search Author Reference
				author_occ = list(self.find_all(i, file_content))
				if not len(author_occ):
					# Check with first name only
					author_occ = list(self.find_all(i.split(" ")[0], file_content))
				if not len(author_occ):
					continue
				for j in author_occ:
					if 'et al' in file_content[j: j+7]:
						self.author_ref_index.append([i, j])
			print "Author References : ", self.author_ref_index
			# Tokenizing for Finding Frequency Distribution of Sections of Paper
			tokens = filter(lambda x: not x in self.stopwords, nltk.word_tokenize(file_content))
			text = nltk.Text(tokens)
			print text.__str__()
			print "Searching for Sections in Paper"
			fd = nltk.FreqDist(vs for word in tokens \
				for vs in re.findall(r'Introduction|Reference|Method|Result|Discussion|Conclusion', word))
			self.section_occ = {}
			for i in fd.most_common(7):
				self.section_occ[i[0]] = list(self.find_all(file_content, i[0]))
			print self.section_occ
			# Checking Title Citation
			if len(numeric_citation):
				print "Title Numeric Citation : ", numeric_citation
				citation_index = self.find_all(file_content, "[%s]"%numeric_citation[0])
				print self.find_citation_section(citation_index)
			elif len(self.author_ref_index):
				# Checking Author Citation
				for i in self.author_ref_index:
					print i
					print self.find_citation_section(i[1])
			elif len(title_occ):
				print "Title Index Searching ...."
				for i in title_occ:
					print i
					print self.find_citation_section(i)
			else:
				print "No Reference Found for Authors or Title"
			
		else:
			print "======= No Reference Found !! ========="
		return

	def find_all(self, a_str, sub):
	    start = 0
	    while True:
        	start = a_str.find(sub, start)
	        if start == -1: return
        	yield start
	        start += len(sub)

	
	def find_citation_section(self, citation_index):
		occ_dict = {'concl_ref': [],
			'method_conl': [],
			'intro_method': []}
		occ_data = {'concl_ref': "Conclucion - Reference",
                        'method_conl': "Method - Conclucion",
                        'intro_method': "Intro - Method"}
		ref_exists = False
		print "Checking position of citation index under sections"
		# Check if Reference Index exists and citation index is less than it
		if 'Reference' in self.section_occ and len(self.section_occ['Reference']):
			ref_exists = True
			if not len(filter(lambda x: citation_index < x, self.section_occ['Reference'])):
				print "Exit : Citation is not above Reference Index"
				print self.section_occ['Reference']
				return "-"
		# Checking if it exists between Discussion/Conclusion/Result and Reference
		concl_index = []
		if len(list(set(['Discussion', 'Conclusion', 'Result']) - set(self.section_occ.keys()))):
			# If Reference Exists, Get relevant Conclusion Indexes
			concl_index = list(itertools.chain(filter(lambda x: x in ['Discussion', 'Conclusion', 'Result'],
                                        self.section_occ)))
			if ref_exists:
				concl_index = filter(lambda x: x < self.section_occ['Reference'][-1], concl_index)
			if len(concl_index):
				concl_citation_index = filter(lambda x : x < citation_index, concl_index)
				if len(concl_citation_index):
					print "Citation Index > Conclusion/Discussion/Result Index"
					print concl_citation_index
					occ_dict['concl_ref'] = concl_citation_index
		# Checking if it exists between Method and Discussion/Conclusion/Result
		method_index = None
		if 'Method' in self.section_occ and len(self.section_occ['Method']):
			method_index = self.section_occ['Method'][0]
			if len(concl_index) and len(self.section_occ['Method']) > 1:
				# If Discussion/Conclusion/Result exists and multiple Method Index exists, Get relevant Method Indexes
				rel_count = {x: len(filter(lambda y: x < y ,concl_index)) for x in self.section_occ['Method']}
				print "Relevance of method indexes : ", rel_count
				method_index = max(rel_count.iteritems(), key=operator.itemgetter(1))[0]
			if method_index < citation_index:
				occ_dict['method_conl'] = [method_index]
		# Checking if it exists between Introduction and Method
                if 'Introduction' in self.section_occ and len(self.section_occ['Introduction']):
			intro_index = min(self.section_occ['Introduction'])[0]
			# If Method Index exists and citation in between them 
			if method_index and citation_index < method_index:
                                occ_dict['method_conl'] = [intro_index]
			# If Conclusion Index exists and citation index is above it
			elif concl_index and not len(occ_dict['concl_ref']):
				occ_dict['method_conl'] = [intro_index]
		# Building Occurance Data
		print occ_dict
		for i,v in occ_dict:
			print occ_data[i]
			for j in v:
				print self.file_content[j - 20: j + 20]
		return occ_dict


