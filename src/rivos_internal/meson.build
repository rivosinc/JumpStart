# SPDX-FileCopyrightText: 2023 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

jumpstart_rivos_internal_sources = files(
                          'start.rcode.S',
                          'imsic_functions.supervisor.c',
                          'jump_to_main.machine.S',
                          'string_functions.supervisor.c',
                          'uart_functions.supervisor.c',
                          'end.machine.S',
                          )

jumpstart_source_attributes_yaml = files('jumpstart_internal_source_attributes.yaml')

# (Should match cad/cfg/.envmod from rvsys)
rivos_spike_isa_string = 'rv64gchv_zba_zbb_zbc_zbs_zbkb_sstc_svpbmt_svinval_sscofpmf_zicbom_zicbop_zicboz_zfh_zfhmin_zfbfmin_zvfh_zvfhmin_zvfbfmin_zvfbfwma_zkt_zkr_zicsr_zifencei_zihintpause_zawrs_zicond_zvkned_zvbb_zvkg_zvknha_zvknhb_zvksh_zvksed_xrivostime_xrivospagewalk_xrivoscode_smaia_ssaia'
rivos_spike_args = ['--pass-fail']

rivos_gcc_march_string = 'rv64gcv_svinval_zba_zbb_zbs_zicbom_zicbop_zicboz_zfh_zfhmin_zfbfmin_zicond_zihintntl_xrivosrcode'
