CMS analysis toolkit
====================

Repo containing simple generic scripts etc. for analysing CMS data


Listing triggers (and prescales) used online
--------------------------------------------

The ``findTriggerPathPrescaleRanges.py`` script runs over CSV-format trigger information produced by the brilcalc tool; it prints to screen the continuous run/LS ranges - within a user-supplied JSON-format run/LS mask - for which the HLT trigger path version number, prescale and L1 seed remained constant.

You can check what arguments the script requires by running ``python findTriggerPathPrescaleRanges.py -h``

For example, to investigate the prescales of PFHT trigger during 2016, you should first run::

  brilcalc trg --hltpath HLT_PFHT???_v? --prescale -o brilcalc-trigger-pfht-prescaleChanges.txt

Then, run the ``findTriggerPathPrescaleRanges.py`` script over this output, and a JSON file for 2016's good run/LS ranges::

  python findTriggerPathPrescaleRanges.py Cert_271036-284044_13TeV_23Sep2016ReReco_Collisions16_JSON.txt brilcalc-trigger-pfht-prescaleChanges.csv
