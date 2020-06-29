/*
A KBase module: NetworkInference
*/

module NetworkInference {

    /* An X/Y/Z style reference */
    typedef string obj_ref;

    typedef structure {
        obj_ref input_tbl;
        string workspace_name;
        string output_suffix;
      } MIIAParams;

    typedef structure {
        string report_name;
        string report_ref;
    } MIIAOutput;

    /* run_miia: perform MIIA*/
    funcdef run_miia(MIIAParams params) returns (MIIAOutput output) authentication required;

};
