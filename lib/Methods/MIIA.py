# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os
import uuid
import pandas as pd
import numpy as np

from Methods.MIIACore import MIIACore
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.KBaseReportClient import KBaseReport
#END_HEADER


class MIIA:
    '''
    Module Name:
    MIIA

    Module Description:
    A KBase module: MIIA
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = ""
    GIT_COMMIT_HASH = ""

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.shared_folder = config['scratch']
        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)
        

    def run_miia(self, params):
        """
        This example function accepts any number of parameters and returns results in a KBaseReport
        :param params: instance of mapping from String to unspecified object
        :returns: instance of type "ReportResults" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String
        """
        # return variables are: output
        
        uuid_string = str(uuid.uuid4())
        
        output_files = []
        
        #######################################################################
        #  check out the input table
        #######################################################################
        print ("Input parameter", params['input_tbl'])
        dfu = DataFileUtil(self.callback_url)
        input_tbl = dfu.get_objects({'object_refs': [params['input_tbl']]})['data'][0]

        print(input_tbl['data']['instances'])

        growth_data = dict()
        for key in input_tbl['data']['instances']:
            idx = int(key)
            # growth_data[key] = np.genfromtxt(input_tbl['data']['instances'][key])
            growth_data[idx] = []
            for val in input_tbl['data']['instances'][key]:
                if val == '': growth_data[idx].append(np.nan)
                else: growth_data[idx].append(float(val))
        
        print(growth_data)

        tbl_cols = [info['attribute'] for info in input_tbl['data']['attributes']]
        tbl_df = pd.DataFrame.from_dict(growth_data, orient='index', columns=tbl_cols).sort_index()

        print(tbl_cols)
        print(tbl_df)

        tbl_df = tbl_df.astype(float)
        
        #######################################################################
        #  compute miia1 and miia2
        #######################################################################
        matrices = []
        nonzeros = []

        miia = MIIACore(tbl_df)
        bmat_1, cmat_1, bmat_2, cmat_2 = miia.runBatch(debug=False)
        # print(bmat_1)
        # print(cmat_1)
        # print(bmat_2)
        # print(cmat_2)

        # replace inf to nan
        for x in [bmat_1, bmat_2, cmat_1, cmat_2]:
            x[x == -np.inf] = np.nan
            x[x == np.inf] = np.nan
            matrices.append(x)
            nonzeros.append(x.size - np.count_nonzero(np.isnan(x)))

        #######################################################################
        #  compute complex with filling undefined binary coefficients as zeros
        #######################################################################
        bmat1 = np.nan_to_num(bmat_1)
        bmat2 = np.nan_to_num(bmat_2)
        complex1 = miia.getComplexFromBinary(bmat1, method='miia1', debug=False)
        complex2 = miia.getComplexFromBinary(bmat2, method='miia2', debug=False)

        # print(complex1)
        # print(complex2)
        
        for x in [complex1, complex2]:
            x[x == -np.inf] = np.nan
            x[x == np.inf] = np.nan
            matrices.append(x)
            nonzeros.append(x.size - np.count_nonzero(np.isnan(x)))

        print("nonzeros:", nonzeros)

        #######################################################################
        # html report
        #######################################################################

        html_folder = os.path.join(self.shared_folder, 'html')
        os.mkdir(html_folder)

        mat_types = ["BinaryInteractions","ComplexInteractions","AdjustedComplexInteractions"]
        methods = ["MIIA","sMIIA"]
        plot_names = ["{}_{}.png".format(i,j) for i in mat_types for j in methods]
        plot_paths = [os.path.join(html_folder, i) for i in plot_names]

        plot_titles = [
            "Pairwise interactions in binary communities with MIIA",
            "Pairwise interactions in binary communities with s-MIIA",
            "Pairwise interactions in complex communities with MIIA",
            "Pairwise interactions in complex communities with s-MIIA",
            "Pairwise interactions in complex communities with MIIA (Adjusted)",
            "Pairwise interactions in complex communities with s-MIIA (Adjusted)",
        ]

        plot_descs = [
            "Pairwise interactions in binary communities with MIIA",
            "Pairwise interactions in binary communities with s-MIIA",
            "Pairwise interactions in complex communities with MIIA",
            "Pairwise interactions in complex communities with s-MIIA",
            "Pairwise interactions in complex communities with MIIA by setting up undefined binary interactions as zeros",
            "Pairwise interactions in complex communities with s-MIIA by setting up undefined binary interactions as zeros"
        ]
        
        for f, mat, num in zip(plot_paths, matrices, nonzeros):
            if num == 0: continue
            miia.drawHeatmap(mat, tbl_cols, f)
            output_files.append({'path': f, 'name': f.rsplit("/",1)[1],
                                'label': f.rsplit("/",1)[1],
                                'description': f.rsplit("/",1)[1]})

        #######################################################################
        # html render
        #######################################################################
        content = ''
        for f, num, title, desc in zip(plot_names, nonzeros, plot_titles, plot_descs):
            substr = ''
            substr += '<div class="col-md-6">'
            substr += '<div class="card mb-6 box-shadow">'
            if num > 0:
                substr += '<img class="card-img-top" alt="{0}" src="{0}" style="width: 100%; display: block;">'
            substr += '<div class="card-body">'
            substr += '<h5 class="card-title">{1}</h5>'
            if num > 0:
                substr += '<p class="card-text">{2}</p>'
            else:
                substr += '<p class="card-text">All interactions are unidentified.</p>'
            substr += '<div class="d-flex justify-content-between align-items-center">'
            substr += '<div class="btn-group">'
            substr += '</div>'
            substr += '</div>'
            substr += '</div>'
            substr += '</div>'
            substr += '</div>'
            
            content += substr.format(f, title, desc)

        with open(os.path.join(os.path.dirname(__file__), 'templates', 'template.html'),
                  'r') as template_file:
            report_html = template_file.read()
            report_html = report_html.replace('<!--[MIIA Results]-->', content)
            
        with open(os.path.join(html_folder, "index.html"), 'w') as index_file:
            index_file.write(report_html)


        report = KBaseReport(self.callback_url)
        html_dir = {
            'path': html_folder,
            'name': 'index.html',
            'description': 'MIIA Report'
        }
        report_info = report.create_extended_report({
            # 'objects_created': objects_created,
            'file_links': output_files,
            'html_links': [html_dir],
            'direct_html_link_index': 0,
            'report_object_name': 'miia_report_' + params['output_suffix'],
            'workspace_name': params['workspace_name']
        })

        output = {
            'report_name': report_info['name'],
            'report_ref': report_info['ref'],
        }

        return output

