//This file defined best1000 charger register address and it`s meaning on very bit
//
//
#define charge_reg_total_num 119

typedef struct {
    int    charge_address;
    int    defaul_value;
    char   *charge_bit_meaing[16];
} CHARGE_Register_ST;

#define charge_value_default {\
{0x0,\
0x0000,\
" ",\
" ",\
" ",\
"revid_charger[3:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"chip_id[15:4]",\
},\
{0x1,\
0x0000,\
"reg_pp_en",\
"reg_pp_en_dr",\
"reg_sys_det_en",\
"reg_sys_det_en_dr",\
"reg_bat_fet_off",\
"reg_bat_fet_off_dr",\
"reg_en_tran_enhance",\
"reg_en_tran_enhance_dr",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_recharge_en",\
"reg_charger_recharge_en_dr",\
"reg_vdet_ot_en",\
"reg_vdet_ot_en_dr",\
},\
{0x2,\
0x0000,\
"reg_bg_core_en",\
"reg_bg_core_en_dr",\
" ",\
" ",\
"reg_charger_thermal_reg_en",\
"reg_charger_thermal_reg_en_dr",\
"reg_charger_ss_pup_en",\
"reg_buck_dc_en",\
"reg_buck_dc_en_dr",\
"reg_buck_en_iin_dpm",\
"reg_buck_en_iin_dpm_dr",\
"reg_buck_en_vin_dpm",\
"reg_buck_en_vin_dpm_dr",\
"reg_charger_trickle_charge_en",\
"reg_charger_trickle_charge_en_dr",\
" ",\
},\
{0x3,\
0x0000,\
"reg_charger_charge_en",\
"reg_charger_charge_en_dr",\
"reg_charger_cc_cv_charge_en",\
"reg_charger_cc_cv_charge_en_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_icharge_ramp_cnt[9:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x4,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_ipre_sel[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_icc_sel[13:7]",\
"reg_charger_icc_sel_dr",\
" ",\
},\
{0x5,\
0x0000,\
"reg_recharge_det_en",\
"reg_recharge_det_en_dr",\
"reg_vsys_oc_det_en",\
"reg_vsys_oc_det_en_dr",\
"reg_vsys_uv_det_en",\
"reg_vsys_uv_det_en_dr",\
"reg_charger_bat_ovp_det_en",\
"reg_charger_bat_ovp_det_en_dr",\
"reg_charger_iterm_det_en",\
"reg_charger_iterm_det_en_dr",\
"reg_dc_en",\
"reg_dc_en_dr",\
"reg_en_iin_dpm",\
"reg_en_iin_dpm_dr",\
"reg_en_vin_dpm",\
"reg_en_vin_dpm_dr",\
},\
{0x6,\
0x0000,\
"reg_pp_en_cl",\
"reg_pp_en_cl_dr",\
"reg_pp_en_cv",\
"reg_pp_en_cv_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x7,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rtc_trim_osc[6:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_precharge_en",\
"reg_charger_precharge_en_dr",\
},\
{0x9,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pp_gm_cl[8:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xa,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_charger_tst_sel[4:0]",\
"reg_charger_tst_mode_en",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_voreg[10:6]",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_pre[15:11]",\
},\
{0xb,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_iterm[4:0]",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_cc[9:5]",\
" ",\
"reg_charger_pre2cc_vbit[11:10]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_iterm_sel[6:0]",\
" ",\
" ",\
"reg_charger_gm_cv[9:7]",\
" ",\
" ",\
"reg_charger_gm_cc[12:10]",\
" ",\
" ",\
"reg_charger_cv_comp_res[15:13]",\
},\
{0xd,\
0x0000,\
" ",\
" ",\
"reg_charger_cv_comp_cap[2:0]",\
" ",\
" ",\
"reg_charger_cc_comp_res[5:3]",\
" ",\
" ",\
"reg_charger_cc_comp_cap[8:6]",\
" ",\
"reg_charger_bat_ovp_vbit[10:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xe,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_bg_trim[5:0]",\
" ",\
" ",\
" ",\
"reg_bg_temp_trim[9:6]",\
"reg_bg_aux_buf_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xf,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_ot_bit[4:3]",\
" ",\
"reg_recharge_vbit[6:5]",\
" ",\
"reg_vin_ov_vbit[8:7]",\
" ",\
"reg_charger_thermal_bit[10:9]",\
" ",\
"reg_vin_ok_vbit[12:11]",\
" ",\
" ",\
" ",\
},\
{0x10,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_tst_ana_digout[4:0]",\
" ",\
" ",\
" ",\
"reg_tst_ana_trim[8:5]",\
"reg_tst_dc_forcenon",\
"reg_tst_dc_forcepon",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x11,\
0x0000,\
"reg_pp_ss",\
"reg_pp_ss_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pp_ss_pos_time[10:2]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x12,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_icc_start[6:0]",\
" ",\
" ",\
"reg_charger_icc_step[9:7]",\
"reg_ramp_up_time_sel",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x13,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_func_reset_10ms[11:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1e,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_fet_reset_10ms_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1f,\
0x0000,\
"reg_command_0_enable",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_command_0_bit_width_tolerance[8:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x20,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_command_0_time[11:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x21,\
0x0000,\
"reg_simutime_scaledown",\
"fet_reset",\
"reg_sw_charge_en",\
"reg_iterm_en",\
"reg_lpo_on",\
" ",\
" ",\
" ",\
"reg_clk_lpo_stable_cnt[8:5]",\
"reg_en_bat_cl",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x22,\
0x0000,\
"reg_vin_uvlo_n_det_in_intr_raw",\
"reg_vin_uvlo_n_det_in_intr_en",\
"reg_vin_uvlo_n_det_in_intr_mask",\
"reg_vin_uvlo_n_det_in_intr_clr",\
"reg_vin_uvlo_n_det_out_intr_raw",\
"reg_vin_uvlo_n_det_out_intr_en",\
"reg_vin_uvlo_n_det_out_intr_mask",\
"reg_vin_uvlo_n_det_out_intr_clr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x23,\
0x0000,\
"reg_otp_en",\
"reg_vin_oc_en",\
"reg_vsys_sc_en",\
"reg_vin_ov_en",\
"reg_vin_uvlo_n_en",\
"reg_pu_lpo",\
"reg_pu_lpo_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_lpo_off_cnt[14:7]",\
"reg_state_ppcl_en",\
},\
{0x24,\
0x0000,\
"reg_standby_ship_mode",\
"reg_uart_standby_mode",\
"reg_done_sw_recharge",\
"reg_fault_sw_recharge",\
"reg_fault2done",\
"reg_standby_uart_mode",\
"reg_ship_standby_mode",\
"reg_ship_mode_en",\
"reg_ship_mode_en_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x25,\
0x0000,\
"reg_charge_tripre_timeout_intr_raw",\
"reg_charge_tripre_timeout_intr_en",\
"reg_charge_tripre_timeout_intr_mask",\
"reg_charge_tripre_timeout_intr_clr",\
"reg_charge_fast_timeout_intr_raw",\
"reg_charge_fast_timeout_intr_en",\
"reg_charge_fast_timeout_intr_mask",\
"reg_charge_fast_timeout_intr_clr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x26,\
0x0000,\
"reg_vsys_sc_intr_raw",\
"reg_vsys_sc_intr_en",\
"reg_vsys_sc_intr_mask",\
"reg_vsys_sc_intr_clr",\
"reg_vin_ov_intr_raw",\
"reg_vin_ov_intr_en",\
"reg_vin_ov_intr_mask",\
"reg_vin_ov_intr_clr",\
"reg_vin_oc_intr_raw",\
"reg_vin_oc_intr_en",\
"reg_vin_oc_intr_mask",\
"reg_vin_oc_intr_clr",\
"reg_otp_intr_raw",\
"reg_otp_intr_en",\
"reg_otp_intr_mask",\
"reg_otp_intr_clr",\
},\
{0x27,\
0x0000,\
"reg_iterm_intr_raw",\
"reg_iterm_intr_en",\
"reg_iterm_intr_mask",\
"reg_iterm_intr_clr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x28,\
0x0000,\
" ",\
"reg_main_state_change_intr_en",\
"reg_main_state_change_intr_mask",\
"reg_main_state_change_intr_clr",\
" ",\
"reg_pu_state_change_intr_en",\
"reg_pu_state_change_intr_mask",\
"reg_pu_state_change_intr_clr",\
" ",\
"reg_chrg_state_change_intr_en",\
"reg_chrg_state_change_intr_mask",\
"reg_chrg_state_change_intr_clr",\
" ",\
"reg_charge_done_intr_en",\
"reg_charge_done_intr_mask",\
"reg_charge_done_intr_clr",\
},\
{0x29,\
0x0000,\
" ",\
"reg_iterm_pos_db_cnt_sel[1:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2a,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reserved_dig[15:0][15:0]",\
},\
{0x2b,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"chip_addr_i2c[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2c,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reserved_ana[8:0][8:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2d,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reserved_ana[17:9][8:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x30,\
0x0000,\
"chg_mid_buck_uv",\
"chg_mid_boost_uv",\
"vreg_chg_boost_uv",\
"power_on_feedin",\
"pu_osc",\
"pu_rc",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x31,\
0x0000,\
"chg_mid_uv",\
"chg_mid_uv_db",\
"vinGTvbat",\
"vinGTvbat_db",\
"state_dcpfm",\
"state_ppcl",\
"state_ppcv",\
"vbat_low",\
"chg_in_ok",\
"state_idpm",\
"state_vdpm",\
"bat_oc",\
"bat_short",\
" ",\
" ",\
" ",\
},\
{0x32,\
0x0000,\
"vin_uvlo_n",\
"vin_uvlo_n_db",\
"pre2cc",\
"pre2cc_db",\
"iterm",\
"iterm_db",\
"recharge",\
"recharge_db",\
"cv_mode",\
"cv_mode_db",\
"bat_ov",\
"bat_ov_db",\
"vin_oc",\
"vin_oc_db",\
"vin_ov",\
"vin_ov_db",\
},\
{0x33,\
0x0000,\
"otp",\
"otp_db",\
"vsys_sc",\
"vsys_sc_db",\
"dcdc_ss_ok",\
"pp_ss_ok",\
"charger_ss_ok",\
" ",\
" ",\
"power_up_state[9:7]",\
" ",\
"main_state[11:10]",\
" ",\
" ",\
"charge_state[14:12]",\
" ",\
},\
{0x34,\
0x0000,\
"charger_intr",\
"vin_uvlo_n_det_in_intr",\
"vin_uvlo_n_det_out_intr",\
"charge_tripre_timeout_intr",\
"charge_fast_timeout_intr",\
"charge_done_intr",\
"vsys_sc_intr",\
"vin_ov_intr",\
"vin_oc_intr",\
"otp_intr",\
"iterm_intr",\
"main_state_change_intr",\
"pu_state_change_intr",\
"chrg_state_change_intr",\
"r_wdt_intr",\
" ",\
},\
{0x35,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_bat_oc_cnt[15:0]",\
},\
{0x36,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_bat_short_cnt[4:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x37,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_bat_oc_fet_off_cnt[15:0]",\
},\
{0x40,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_clock_sel",\
" ",\
" ",\
" ",\
" ",\
},\
{0x43,\
0x0000,\
"reg_standby_ship_mode_en",\
"reg_ship_standby_mode_en",\
"reg_uart_standby_mode_en",\
"reg_standby_uart_mode_en",\
"reg_done_sw_recharge_en",\
"reg_fault_sw_recharge_en",\
"reg_fault2done_en",\
"charger_trickle_charge_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x4b,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_standby_ship_cnt[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x4e,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pp_ldo_soft_start_cnt[7:0]",\
"reg_charger_soft_start_dr",\
"reg_charger_soft_start",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x4f,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_soft_start_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x50,\
0x0000,\
" ",\
" ",\
" ",\
"reg_dc_cc              [3:0]",\
" ",\
" ",\
"reg_dc_com_c           [6:4]",\
" ",\
"reg_dc_com_cf          [8:7]",\
" ",\
" ",\
"reg_dc_com_r           [11:9]",\
" ",\
" ",\
" ",\
"reg_dcdc_boost_en",\
},\
{0x51,\
0x0000,\
" ",\
" ",\
" ",\
"reg_dc_drvnn           [3:0]",\
" ",\
" ",\
" ",\
"reg_dc_drvnp           [7:4]",\
" ",\
" ",\
" ",\
"reg_dc_drvpn           [11:8]",\
" ",\
" ",\
" ",\
"reg_dc_drvpp           [15:12]",\
},\
{0x52,\
0x0000,\
" ",\
"reg_dc_ea_clpl         [1:0]",\
" ",\
" ",\
" ",\
"reg_dc_dtnon           [5:2]",\
" ",\
" ",\
" ",\
"reg_dc_dtpon           [9:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_cvout           [15:10]",\
},\
{0x53,\
0x0000,\
" ",\
" ",\
" ",\
"reg_dc_eco_det_setupt  [3:0]",\
" ",\
"reg_dc_en_dulp_comp    ",\
"reg_dc_enanring        ",\
"reg_dc_encc            ",\
" ",\
"reg_dc_ea_clph         [9:8]",\
"reg_dc_eneaclph        ",\
"reg_dc_eneaclpl        ",\
"reg_dc_eneco           ",\
"reg_dc_enoc            ",\
"reg_dc_enpd            ",\
" ",\
},\
{0x54,\
0x0000,\
" ",\
"reg_dc_enzc            ",\
" ",\
"reg_dc_f               [3:2]",\
" ",\
" ",\
"reg_dc_gmcc            [6:4]",\
" ",\
" ",\
"reg_dc_gmcv            [9:7]",\
"reg_dc_mode            ",\
"reg_dc_mode_buck       ",\
"reg_dc_enpgm_dr",\
"reg_sleep_allow",\
"reg_rc_sleep_allow",\
"reg_dc_enpfm_normal",\
},\
{0x55,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_oc_n_pfm_boost  [7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_oc_n_pwm_boost  [15:8]",\
},\
{0x56,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_oc_n_pwm_buck   [7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_oc_p_pfm_buck   [15:8]",\
},\
{0x57,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_oc_p_pwm_boost  [7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_oc_p_pwm_buck   [15:8]",\
},\
{0x58,\
0x0000,\
"reg_dc_drvnn_p_fb  ",\
"reg_dc_drvpp_p_fb  ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_pll_delay       [7:5]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_ramp_c          [13:11]",\
"reg_dc_ss              ",\
" ",\
},\
{0x59,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_boost_eco_vbit[5:0]",\
" ",\
"reg_dc_com_cf_buck[7:6]",\
" ",\
" ",\
" ",\
"reg_dc_trim_iin_dpm[11:8]",\
" ",\
" ",\
" ",\
"reg_dc_vin_dpm_sel[15:12]",\
},\
{0x5a,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_dc_id_deltav_vbit_default[4:0]",\
" ",\
" ",\
" ",\
" ",\
"reg_nvdc_deltav_vbit[9:6]",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_id_deltav_vbit_start[14:10]",\
"reg_dc_id_deltav_vbit_dr",\
},\
{0x5b,\
0x0000,\
" ",\
" ",\
"reg_dc_gm_vsys_min[2:0]",\
" ",\
" ",\
"reg_dc_gm_iin_dpm[5:3]",\
" ",\
" ",\
"reg_dc_gm_vin_dpm[8:6]",\
" ",\
" ",\
" ",\
"reg_dc_fc_comp_hys[12:9]",\
"reg_dc_osn_sel",\
" ",\
"reg_dc_id_ramp_cnt[15:14]",\
},\
{0x5c,\
0x0000,\
"reg_dc_dt_fb",\
"reg_dc_en_zcd_cal",\
"reg_dc_reset_zcd_cnt",\
"reg_dc_reset_zcd_dlatch",\
" ",\
" ",\
" ",\
"reg_dc_zcd_cap_bit[7:4]",\
" ",\
" ",\
" ",\
"reg_dc_zcd_delay[11:8]",\
" ",\
" ",\
" ",\
"reg_dc_id_ramp_step[15:14]",\
},\
{0x5d,\
0x0000,\
"reg_dc_zcn_cnt",\
"reg_dc_zcp_cnt",\
"reg_dc_tst_force_noff",\
"reg_dc_tst_force_poff",\
" ",\
"reg_dc_zcn_release_cnt[5:4]",\
" ",\
"reg_dc_zcp_release_cnt[7:6]",\
" ",\
"reg_dc_det_debounce[9:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_trim_pwr_osc2m[15:10]",\
},\
{0x5e,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_reserved[15:0][15:0]",\
},\
{0x5f,\
0x0000,\
" ",\
"reg_dc_reserved[17:16][1:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x60,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_zc_n            [7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_dc_zc_p            [15:8]",\
},\
{0x61,\
0x0000,\
" ",\
" ",\
" ",\
"reg_trim_ana_iref      [3:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x62,\
0x0000,\
" ",\
" ",\
" ",\
"reg_trim_dc_vout       [3:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_trim_pp_cl         [11:8]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x63,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_trim_pp_clgr       [7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_trim_pp_clos       [15:8]",\
},\
{0x64,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_trim_pp_csgr       [7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_trim_pp_csos       [15:8]",\
},\
{0x65,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_trim_pp_csosacc    [6:0]",\
" ",\
" ",\
"reg_trim_pwr_ecov      [9:7]",\
" ",\
" ",\
" ",\
"reg_trim_pp_csclgr     [13:10]",\
" ",\
" ",\
},\
{0x66,\
0x0000,\
" ",\
" ",\
" ",\
"reg_trim_bg_aux[3:0]",\
" ",\
" ",\
" ",\
" ",\
"reg_trim_pp_cv[8:4]",\
" ",\
" ",\
" ",\
"reg_trim_pp_id[12:9]",\
" ",\
" ",\
" ",\
},\
{0x75,\
0x0000,\
" ",\
" ",\
" ",\
"reg_psw_boost_ss_pos_db_cnt[3:0]",\
"reg_psw_boost_ss_neg_db_cnt",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x80,\
0x0000,\
" ",\
" ",\
" ",\
"reg_pu_vdet_cnt[3:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x81,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_pp_cl[4:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pp_cv[12:5]",\
"reg_pp_en_isnk10m",\
"reg_pp_en_isnk500u",\
"reg_pp_enid",\
},\
{0x82,\
0x0000,\
" ",\
" ",\
"reg_pp_gm_cv[2:0]",\
" ",\
"reg_pp_outoc[4:3]",\
" ",\
"reg_pp_state[6:5]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x83,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_psw_boost_cv[7:0]",\
"reg_psw_boost_en",\
"reg_psw_boost_encv",\
" ",\
" ",\
"reg_psw_boost_gm_cv[12:10]",\
"reg_psw_boost_en_dr",\
"reg_psw_boost_ss_dr",\
"reg_psw_boost_ss",\
},\
{0x84,\
0x0000,\
" ",\
" ",\
" ",\
"reg_vsys_min_sel[3:0]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_cl[8:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x85,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_rds_icc[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_rds_iterm[15:8]",\
},\
{0x86,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_osn_cs_icc[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_osn_cs_iterm[13:7]",\
" ",\
" ",\
},\
{0x87,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_osp_cs_icc[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_trim_osp_cs_iterm[13:7]",\
" ",\
" ",\
},\
{0x88,\
0x0000,\
"reg_charger_fr_en",\
" ",\
" ",\
"reg_charger_id_deltav_vbit[3:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x89,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_charger_voreg_bit[6:0]",\
" ",\
" ",\
"reg_charger_vsys_min_vbit[9:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x8a,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_cl_vos_bit[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x8b,\
0x0000,\
" ",\
" ",\
" ",\
"reg_itrickle_sel[3:0]",\
" ",\
"reg_ana_chgmid_uv[5:4]",\
" ",\
"reg_ana_vsys_sc[7:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x90,\
0x0000,\
"reg_wdt_reset_en",\
"reg_wdt_en",\
"reg_wdt_load",\
"reg_wdt_load_intr",\
"wdt_intr_clr",\
"reg_wdt_intr_en",\
"reg_wdt_intr_mask",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x91,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_wdt_timer[15:0]",\
},\
{0x92,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_wdt_timer_intr[15:0]",\
},\
{0xa0,\
0x0000,\
"reg_efuse_pgm_read_sel",\
"reg_efuse_clk_en",\
"reg_efuse_turn_on",\
"reg_efuse_strobe_trigger",\
" ",\
"reg_efuse_clk_osc_sel",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xa1,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_address[7:0]",\
" ",\
" ",\
" ",\
" ",\
"reg_base_addr[12:8]",\
" ",\
" ",\
" ",\
},\
{0xa2,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_data_out[7:0]",\
"reg_efuse_data_out_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xa3,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_power_on_read_address[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_power_on_read_inc[12:7]",\
" ",\
" ",\
" ",\
},\
{0xa4,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_addr_inc[5:0]",\
" ",\
" ",\
" ",\
"reg_sq_time[9:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xa5,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_pgm_en_time[8:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_addr_en_time[14:9]",\
" ",\
},\
{0xa6,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_strobe_pre_time[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_pgm_strobe_time[14:6]",\
" ",\
},\
{0xa7,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_read_strobe_time[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_pgm_cold_time[14:6]",\
" ",\
},\
{0xa8,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_read_cold_time[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_avdd_dis_time[11:6]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xa9,\
0x0000,\
"reg_efuse_rden_dr",\
"reg_efuse_pu_avdd_dr",\
"reg_efuse_pgmen_dr",\
"reg_efuse_aen_dr",\
"reg_efuse_rden",\
"reg_efuse_pu_avdd",\
"reg_efuse_pgmen",\
"reg_efuse_aen",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xaa,\
0x0000,\
"efuse_read_end",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"efuse_data_out[8:1]",\
" ",\
" ",\
" ",\
"efuse_fsm[12:9]",\
" ",\
" ",\
" ",\
},\
{0xc0,\
0x0000,\
"reg_xo_32k_pu_ldo_dr",\
"reg_xo_32k_pu_ldo",\
" ",\
" ",\
"reg_xo_32k_ldo_precharge_value[4:2]",\
"reg_xo_32k_ldo_precharge_dr",\
"reg_xo_32k_ldo_precharge",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_xo_32k_isel_ramp_start_dly[15:7]",\
},\
{0xc1,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_xo_32k_isel_ramp_t_step[4:0]",\
"reg_xo_32k_isel_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_xo_32k_isel_value[11:6]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc2,\
0x0000,\
"reg_clk_rtc_sel_xo",\
"reg_xo_32k_1hz_bypass",\
" ",\
" ",\
"reg_aon_32k_xo_sel[4:2]",\
"reg_xo_32k_gate",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc3,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_clk_32k_xo_div_1hz[15:0]",\
},\
{0xc4,\
0x0000,\
"reg_rtc_load",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc5,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rtc_time_load_value[15:0][15:0]",\
},\
{0xc6,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rtc_time_load_value[31:16][15:0]",\
},\
{0xc7,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rtc_date_load_value[15:0][15:0]",\
},\
{0xc8,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rtc_date_load_value[31:16][15:0]",\
},\
{0xc9,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rtc_match_value_time[15:0][15:0]",\
},\
{0xca,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rtc_match_value_time[31:16][15:0]",\
},\
{0xcb,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rtc_match_value_date[15:0][15:0]",\
},\
{0xcc,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rtc_match_value_date[31:16][15:0]",\
},\
{0xcd,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"cfg_div_rtc_1hz[15:0]",\
},\
{0xce,\
0x0000,\
"reg_rtc_int_clr",\
"reg_rtc_int_en",\
"rtc_intr",\
"reg_rtc_int_mask",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xcf,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"rtc_time_value[15:0][15:0]",\
},\
{0xd0,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"rtc_time_value[31:16][15:0]",\
},\
{0xd1,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"rtc_date_value[15:0][15:0]",\
},\
{0xd2,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"rtc_date_value[31:16][15:0]",\
},\
{0xd3,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_xo_32k_capbit_lv[8:0]",\
" ",\
"reg_xo_32k_drv_sel_lv[10:9]",\
" ",\
"reg_xo_32k_ext1_en_lv",\
"reg_xo_32k_ext2_en_lv",\
"reg_xo_32k_ext3_en_lv",\
"reg_xo_32k_pwr_sel_lv",\
},\
{0xd4,\
0x0000,\
"reg_chg_mid_uv_intr_mux",\
"reg_chg_mid_buck_uv_intr_mux",\
"reg_chg_mid_boost_uv_intr_mux",\
"reg_vreg_chg_boost_uv_intr_mux",\
"reg_state_dcpfm_intr_mux",\
"reg_state_idpm_intr_mux",\
"reg_state_vdpm_intr_mux ",\
"reg_state_ppcl_intr_mux",\
"reg_state_ppcv_intr_mux",\
"reg_bat_oc_intr_mux",\
"reg_bat_short_intr_mux",\
" ",\
" ",\
" ",\
" ",\
" ",\
}\
}