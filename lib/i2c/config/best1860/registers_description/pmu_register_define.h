//This file defined pmu register address and it`s meaning on very bit
//
//

#define pmu_reg_total_num 725

typedef struct {
    int    pmu_address;
    int    defaul_value;
    char   *pmu_bit_meaing[16];
} PMU_Register_ST;

#define pmu_value_default {\
{0x0,\
0x0000,\
"chipid_old[15:4]",\
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
"revid[3:0]",\
" ",\
" ",\
" ",\
},\
{0x1,\
0x0000,\
"chipid_new[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"chipid_string[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x3,\
0x0000,\
"reg_vsense_sel_vmem",\
"pu_lp_bias_ldo_dsleep",\
"pu_lp_bias_ldo_dr",\
"pu_lp_bias_ldo_reg",\
"pu_bias_ldo_dr",\
"pu_bias_ldo_reg",\
"bg_vbg_sel_dr",\
"bg_vbg_sel_reg",\
"bg_constant_gm_bias_dr",\
"bg_constant_gm_bias_reg",\
"bg_core_en_dr",\
"bg_core_en_reg",\
"reg_pu_ldo_02_dr",\
"reg_pu_ldo_02",\
"bg_notch_en_dr",\
"bg_notch_en_reg",\
},\
{0x4,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_soft_start2",\
" ",\
" ",\
" ",\
" ",\
"reg_clk_rccal_div[2:0]",\
" ",\
" ",\
},\
{0x5,\
0x0000,\
"reg_pu_ldo_vrtc_rf_dsleep",\
"reg_pu_ldo_vrtc_rf_dr",\
"reg_pu_ldo_vrtc_rf_reg",\
"reg_charge_out_intr_msk",\
"reg_charge_in_intr_msk",\
"reg_ac_on_out_en",\
"reg_ac_on_in_en",\
"reg_charge_intr_en",\
"reg_ac_on_db_value[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x6,\
0x0000,\
" ",\
"reg_bypass_vbg_rf_buffer",\
" ",\
"reg_pu_vbg_rf_buffer",\
"bg_notch_lpf_low_bw",\
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
"reg_ldo_02_pulldown",\
"reg_lp_en_ldo_02_dsleep",\
"reg_lp_en_ldo_02_dr",\
"reg_lp_en_ldo_02",\
"reg_pu_ldo_02_dsleep",\
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
{0x8,\
0x0000,\
"reg_dcdc_clk_se_en",\
"reg_lp_en_ldo_05_dsleep",\
"reg_lp_en_ldo_05_dr",\
"reg_lp_en_ldo_05",\
"reg_pu_ldo_05_dsleep",\
"reg_pu_ldo_05_dr",\
"reg_pu_ldo_05",\
"reg_ldo_13_pulldown",\
" ",\
" ",\
" ",\
"reg_ldo_05_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_05_ramp_en",\
},\
{0x9,\
0x0000,\
"reg_lp_en_ldo_06_dsleep",\
"reg_lp_en_ldo_06_dr",\
"reg_lp_en_ldo_06",\
"reg_pu_ldo_06_dsleep",\
"reg_pu_ldo_06_dr",\
"reg_pu_ldo_06",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_06_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_06_ramp_en",\
},\
{0xa,\
0x0000,\
"reg_lp_en_ldo_03_dsleep",\
"reg_lp_en_ldo_03_dr",\
"reg_lp_en_ldo_03",\
"reg_pu_ldo_03_dsleep",\
"reg_pu_ldo_03_dr",\
"reg_pu_ldo_03",\
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
{0xb,\
0x0000,\
"reg_hw_wdt_rst_time[15:4]",\
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
"resetn_db_number[3:0]",\
" ",\
" ",\
" ",\
},\
{0xc,\
0x0000,\
"reg_lp_en_ldo_13_dsleep",\
"reg_lp_en_ldo_13_dr",\
"reg_lp_en_ldo_13",\
"reg_pu_ldo_13_dsleep",\
"reg_pu_ldo_13_dr",\
"reg_pu_ldo_13",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_13_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_13_ramp_en",\
},\
{0xd,\
0x0000,\
"reg_lp_en_ldo_01_dr",\
"reg_lp_en_ldo_01",\
"reg_pu_ldo_01_dr",\
"reg_pu_ldo_01",\
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
{0xe,\
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
"reg_ldo_06_pulldown",\
"reg_ldo_03_pulldown",\
" ",\
"resetn_db_en",\
},\
{0xf,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"clk_gpio_div_value[8:4]",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_clk_osc_sel",\
"reg_gpio_clk_32k_sel",\
"reg_gpio_osc_clk_en",\
"reg_gpio_rc_clk_en",\
},\
{0x10,\
0x0000,\
"reg_ldo_11_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_11_vbit_normal[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x11,\
0x0000,\
"power_up_soft_cnt[15:11]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"power_up_bias_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x12,\
0x0000,\
"power_up_mod2_cnt[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"power_up_mod1_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x13,\
0x0000,\
"power_up_mod4_cnt[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"power_up_mod3_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x14,\
0x0000,\
"power_up_mod6_cnt[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"power_up_mod5_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x15,\
0x0000,\
"reg_uvlo_sel[15:14]",\
" ",\
"reg_pu_ldo_dig_dr",\
"reg_pu_ldo_dig_reg",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_vref_sel_rc[7:6]",\
" ",\
"reg_buck_01_vref_sel_dsleep[5:4]",\
" ",\
"reg_buck_01_vref_sel_normal[3:2]",\
" ",\
"reg_pu_buck_01_dr",\
"reg_pu_buck_01",\
},\
{0x16,\
0x0000,\
" ",\
" ",\
"chan_en_reg[13:0]",\
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
{0x17,\
0x0000,\
" ",\
"reg_gpadc_en_dr",\
"reg_gpadc_en_reg[13:0]",\
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
{0x18,\
0x0000,\
"reg_temp_en_dr",\
"reg_temp_en",\
"reg_low_temp_en_dr",\
"reg_low_temp_en",\
"reg_temp_clk_en_dr",\
"reg_temp_clk_en",\
"reg_det_gap[9:6]",\
" ",\
" ",\
" ",\
"reg_temp_intr_msk[5:4]",\
" ",\
"reg_temp_intr_en",\
"reg_temp_intr_clr",\
"reg_sar_temp_reset",\
"reg_temp_get_en",\
},\
{0x19,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_zero_temp_refrence[11:0]",\
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
{0x1a,\
0x0000,\
"lpo_off_cnt[15:12]",\
" ",\
" ",\
" ",\
"power_on_db_cnt[11:8]",\
" ",\
" ",\
" ",\
"power_off_cnt[7:4]",\
" ",\
" ",\
" ",\
"clk_stable_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x1b,\
0x0000,\
"reg_pu_vbat_div",\
"reg_pu_poweron_lpo_dr",\
"reg_pu_poweron_lpo",\
"powerkey_wakeup_osc_en",\
"rtc_power_on_en",\
"pu_all_reg",\
"clk_32k_sel[9:8]",\
" ",\
"deepsleep_mode_digi_dr",\
"deepsleep_mode_digi_reg",\
" ",\
" ",\
"reg_ldo_ss_bias_en_dr",\
"reg_ldo_ss_bias_en",\
"reg_32k_gate_en",\
"reg_xo_32k_gate_en",\
},\
{0x1c,\
0x0000,\
"reg_not_set[15:0]",\
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
{0x1e,\
0x0000,\
" ",\
" ",\
"low_temp_intr_msk",\
"reg_gpadc_clk_div_bypass",\
"reg_gpadc_resetn_dr",\
"reg_gpadc_resetn",\
"reg_sar_pwr_bit[9:8]",\
" ",\
" ",\
" ",\
" ",\
"sar_temp_fsm[4:2]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1f,\
0x0000,\
" ",\
"key_db_dsb",\
"key_interval_mode",\
"gpadc_interval_mode",\
"state_reset",\
"sar_adc_mode",\
"delay_before_samp[9:8]",\
" ",\
"conv_clk_inv",\
"samp_clk_inv",\
"time_samp_neg",\
"time_samp_pos",\
"sar_out_polarity",\
"timer_sar_stable_sel[2:0]",\
" ",\
" ",\
},\
{0x20,\
0x0000,\
"reg_clk_gpadc_div_value[15:11]",\
" ",\
" ",\
" ",\
" ",\
"reg_key_in_dr",\
"reg_key_in_reg",\
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
{0x21,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_lp_mode_rtc_dr ",\
"reg_lp_mode_rtc_sel",\
"reg_lp_mode_rtc    ",\
"clk_bg_en",\
"clk_bg_div_value[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x22,\
0x0000,\
"key_interval[15:0]",\
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
{0x23,\
0x0000,\
"gpadc_interval[15:0]",\
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
{0x24,\
0x0000,\
" ",\
"chip_addr_i2c[14:8]",\
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
{0x25,\
0x0000,\
" ",\
"reg_sar_ref_mode_sel",\
"reg_clk_gpadc_en",\
"reg_dr_pu_sar",\
"reg_pu_sar",\
"reg_dr_tsc_sar_bit",\
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
{0x26,\
0x0000,\
" ",\
"rtc_int1_msk",\
"rtc_int0_msk",\
"key_err1_intr_msk",\
"key_err0_intr_msk",\
"key_press_intr_msk",\
"key_release_intr_msk",\
"sample_done_intr_msk",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x27,\
0x0000,\
"reg_bg_sleep_msk",\
" ",\
"rtc_int_en_0",\
"key_err1_intr_en",\
"key_err0_intr_en",\
"key_press_intr_en",\
"key_release_intr_en",\
"sample_done_intr_en",\
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
"reg_dcdc3_dsleep_msk",\
"reg_dcdc2_dsleep_msk",\
"reg_dcdc1_dsleep_msk",\
" ",\
"resetn_dig_dr",\
"resetn_dig_reg",\
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
{0x29,\
0x0000,\
"reg_cnt_coarse_mark_l[15:0]",\
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
{0x2a,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_cnt_coarse_mark_h[8:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2b,\
0x0000,\
" ",\
" ",\
"ext_intr_det_value[13:6]",\
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
{0x2c,\
0x0000,\
" ",\
" ",\
"charger_rtc_intr_msk",\
"cc_intr_msk",\
"charger_intr_msk",\
"gpio_60_intr_msk",\
"power_abort_intr_msk",\
"gpio_60_nedg_intr_msk",\
" ",\
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
" ",\
"low_temp_intr_pmu",\
"power_abort_intr_pmu",\
"gpadc_intr",\
"gpio_60_nedg_intr_pmu",\
"gpio_60_intr_pmu",\
"ext_intr_pmu",\
"pmic_int_pmu",\
},\
{0x2f,\
0x0000,\
"rtc_match_value_time[15:0][15:0]",\
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
{0x30,\
0x0000,\
"rtc_match_value_time[31:16][15:0]",\
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
{0x31,\
0x0000,\
"rtc_match_value_date[15:0][15:0]",\
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
{0x32,\
0x0000,\
"rtc_match_value_date[31:16][15:0]",\
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
{0x37,\
0x0000,\
"cfg_div_rtc_1hz[15:0]",\
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
{0x38,\
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
"ext_charger_rtc_intr",\
"ext_cc_intr",\
"ext_charger_intr",\
},\
{0x39,\
0x0000,\
"reg_led_io1_aio_en",\
"reg_led_io2_aio_en",\
"reg_led_io1_rx_en",\
"reg_led_io2_rx_en",\
"reg_mic_ldoa_en",\
"reg_mic_ldob_en",\
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
{0x3a,\
0x0000,\
"reg_led_io1_ibit[15:14]",\
" ",\
"reg_led_io1_oenb",\
"reg_led_io1_pden",\
"reg_led_io1_pu",\
"reg_led_io1_puen",\
"reg_led_io1_sel[9:8]",\
" ",\
"reg_led_io2_ibit[7:6]",\
" ",\
"reg_led_io2_oenb",\
"reg_led_io2_pden",\
"reg_led_io2_pu",\
"reg_led_io2_puen",\
"reg_led_io2_sel[1:0]",\
" ",\
},\
{0x3b,\
0x0000,\
"reg_mic_biasa_chansel[15:14]",\
" ",\
"reg_mic_biasa_en",\
"reg_mic_biasa_enlpf",\
"reg_mic_biasa_lpfsel[11:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_mic_ldoa_res[4:1]",\
" ",\
" ",\
" ",\
"reg_mic_ldoa_loopctrl",\
},\
{0x3c,\
0x0000,\
"reg_mic_biasb_chansel[15:14]",\
" ",\
"reg_mic_biasb_en",\
"reg_mic_biasb_enlpf",\
"reg_mic_biasb_lpfsel[11:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_mic_ldob_res[4:1]",\
" ",\
" ",\
" ",\
"reg_mic_ldob_loopctrl",\
},\
{0x3d,\
0x0000,\
"reg_clk_cal_en",\
"reg_rcosc_48m_goal_cnt_mark_16",\
"reg_rcosc_48m_polar_sel",\
"reg_rcosc_48m_tun_code_dr",\
"reg_rcosc_48m_calib_en",\
"reg_rcosc_48m_llc_sft_rstn",\
"reg_rcosc_48m_ref_div_num[9:0]",\
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
{0x3e,\
0x0000,\
"reg_rcosc_48m_goal_cnt_mark_15_0[15:0]",\
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
{0x3f,\
0x0000,\
" ",\
" ",\
"reg_rcosc_48m_en_agpio_test",\
" ",\
"reg_rcosc_48m_vout_sel[11:9]",\
" ",\
" ",\
" ",\
"reg_rcosc_48m_pwr_bit[7:6]",\
" ",\
"reg_ref_div[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x40,\
0x0000,\
"reg_rcosc_48m_pu_ldo_dr",\
"reg_rcosc_48m_pu_ldo",\
"reg_rcosc_2m_en_dr",\
"reg_rcosc_2m_en",\
" ",\
" ",\
"reg_rcosc_48m_en_clk_inf_dig",\
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
{0x41,\
0x0000,\
"reg_rcosc_48m_calib_gate",\
"reg_rcosc_48m_tun_code_fine_dr",\
" ",\
"reg_rcosc_48m_osc_fr[12:11]",\
" ",\
"reg_rcosc_48m_tun_code_fine[10:6]",\
" ",\
" ",\
" ",\
" ",\
"reg_rcosc_48m_tun_code[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x42,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_rcosc_48m_clk_inf_dig",\
"reg_rcosc_48m_clk_calib_dig",\
"reg_rcosc_48m_lp_ldo[7:6]",\
" ",\
"reg_rcosc_48m_freq_sel[5:3]",\
" ",\
" ",\
"reg_rcosc_48m_en_clk_dlatch",\
"reg_rcosc_48m_en_clk_calib_dig",\
"reg_rcosc_48m_en_clk48m_to_mux",\
},\
{0x43,\
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
"reg_sar_vref_bit[3:0]",\
" ",\
" ",\
" ",\
},\
{0x44,\
0x0000,\
"reg_cal_lpo_rst",\
"reg_clk_cal_lpo_div[14:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"acout_ldo_on_en",\
" ",\
"sleep_allow",\
"poweron_release_en",\
"poweron_press_en",\
" ",\
" ",\
" ",\
},\
{0x45,\
0x0000,\
"vbat_ovp_poweroff_en",\
" ",\
" ",\
" ",\
"reg_mic_ldob_pulldown",\
"reg_mic_ldoa_pulldown",\
" ",\
"reg_clk_dcdc4_en",\
"reg_clk_dcdc3_en",\
"reg_clk_dcdc2_en",\
"reg_clk_dcdc1_en",\
"reg_clk_dcdc_div[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x46,\
0x0000,\
"reg_buck_01_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_vbit_normal[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x47,\
0x0000,\
"reg_buck_01_vbit_dsleep[15:8]",\
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
{0x4a,\
0x0000,\
" ",\
" ",\
"chan_data_intr_en[13:0]",\
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
{0x4b,\
0x0000,\
" ",\
" ",\
"chan_data_intr_msk[13:0]",\
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
{0x4c,\
0x0000,\
"reg_ldo_02_lv_mode",\
"reg_ldo_09_pulldown",\
"reg_pu_vsys_div",\
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
{0x4d,\
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
"reg_trim_bg_aux[3:0]",\
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
" ",\
" ",\
"reg_lpo_ktrim[6:0]",\
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
"reg_wdt_load",\
"gpio3_data_in",\
"reg_led_io2_data_in",\
"reg_led_io1_data_in",\
" ",\
" ",\
" ",\
"ship_mode_power_off",\
"gpadc_start",\
"key_start",\
"rc_cal_ready",\
"ac_on_en",\
"hardware_power_off_en",\
"soft_power_off",\
},\
{0x50,\
0x0000,\
" ",\
" ",\
"bg_vtoi_en_dr",\
"bg_vtoi_en_reg",\
"reg_tsc_sar_bit[11:0]",\
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
{0x51,\
0x0000,\
" ",\
" ",\
" ",\
"reg_coarse_polar_sel",\
"reg_coarse_tun_code_dr",\
"reg_coarse_en",\
"reg_clk_goal_div_num[9:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_xtal_freq_llc_sft_rstn",\
},\
{0x52,\
0x0000,\
"gpio_intr_clr",\
"gpio_intr_msked",\
"rtc_int_1",\
"rtc_int_clr_0",\
"rtc_int_0",\
"key_err1_intr_clr",\
"key_err1_intr",\
"key_err0_intr",\
"key_err0_intr_clr",\
"key_press_intr",\
"key_press_intr_clr",\
"key_release_intr_clr",\
"key_release_intr",\
"sample_done_intr_clr",\
"sample_period_done_intr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x53,\
0x0000,\
" ",\
"rtc_int1_msked",\
"rtc_int0_msked",\
"key_err1_intr_msked",\
"key_err0_intr_msked",\
"key_press_intr_msked",\
"key_release_intr_msked",\
"sample_done_intr_msked",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x54,\
0x0000,\
" ",\
" ",\
"chan_data_intr_clr[13:0]",\
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
"chan_data_valid_intr[13:0]",\
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
{0x55,\
0x0000,\
" ",\
" ",\
"chan_data_intr_msked[13:0]",\
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
{0x56,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan0[11:0]",\
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
{0x57,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan1[11:0]",\
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
{0x58,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan2[11:0]",\
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
{0x59,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan3[11:0]",\
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
{0x5a,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan4[11:0]",\
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
{0x5b,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan5[11:0]",\
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
{0x5c,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan6[11:0]",\
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
{0x5d,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan7[11:0]",\
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
{0x5e,\
0x0000,\
" ",\
"pu_rc_out",\
"ap_deepsleep_mode",\
"ap_pu_out",\
"reg_power_on_release_clr",\
"power_on_release",\
"reg_power_on_press_clr",\
"power_on_press",\
"power_on",\
"deepsleep_mode",\
"pmu_ldo_on",\
"pu_osc_out",\
"uvlo",\
"intr_msked_charge[4:3]",\
" ",\
"ac_on",\
"ac_on_det_out",\
"reg_charge_out_intr_clr",\
"reg_charge_in_intr_clr",\
"ac_on_det_in",\
},\
{0x5f,\
0x0000,\
" ",\
" ",\
"dig_buck_06_pu",\
"dig_buck_05_pu",\
"dig_buck_04_pu",\
"dig_buck_03_pu",\
"dig_buck_02_pu",\
"dig_buck_01_pu",\
"dig_ldo_09_pu",\
"dig_ldo_08_pu",\
"dig_ldo_07_pu",\
"dig_ldo_06_pu",\
"dig_ldo_05_pu",\
"dig_ldo_03_pu",\
"dig_ldo_02_pu",\
"dig_ldo_01_pu",\
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
" ",\
" ",\
" ",\
"dig_ldo_15_pu",\
"dig_ldo_14_pu",\
"dig_ldo_13_pu",\
"dig_ldo_12_pu",\
"dig_ldo_11_pu",\
"dig_ldo_10_pu",\
},\
{0x61,\
0x0000,\
"reg_xo_32k_ext2_en",\
"reg_xo_32k_ext1_en",\
"reg_xo_32k_isel_value[13:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_xo_32k_isel_dr",\
"reg_xo_32k_pu_ldo_dr",\
"reg_xo_32k_pu_ldo",\
"reg_xo_32k_ldo_precharge_value[4:2]",\
" ",\
" ",\
"reg_xo_32k_ldo_precharge_dr",\
"reg_xo_32k_ldo_precharge",\
},\
{0x62,\
0x0000,\
"reg_xo_32k_pwr_sel",\
"reg_xo_32k_ext3_en",\
"reg_xo_32k_isel_ramp_start_dly[13:5]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_xo_32k_isel_ramp_t_step[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x63,\
0x0000,\
"reg_en_sw1_1p8",\
"reg_en_sw1_1p8_dr",\
"reg_en_sw2_1p8",\
"reg_en_sw2_1p8_dr",\
"reg_en_sw3_1p8",\
"reg_en_sw3_1p8_dr",\
"reg_en_sw4_1p8",\
"reg_en_sw4_1p8_dr",\
"reg_en_sw1_1p8_pull_down[7:6]",\
" ",\
"reg_en_sw2_1p8_pull_down[5:4]",\
" ",\
"reg_en_sw3_1p8_pull_down[3:2]",\
" ",\
"reg_en_sw4_1p8_pull_down[1:0]",\
" ",\
},\
{0x64,\
0x0000,\
"reg_en_sw1_1p8_isel[15:12]",\
" ",\
" ",\
" ",\
"reg_en_sw2_1p8_isel[11:8]",\
" ",\
" ",\
" ",\
"reg_en_sw3_1p8_isel[7:4]",\
" ",\
" ",\
" ",\
"reg_en_sw4_1p8_isel[3:0]",\
" ",\
" ",\
" ",\
},\
{0x65,\
0x0000,\
"reg_id_det1_en",\
"reg_id_det1_isel[14:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_id_det2_en",\
"reg_id_det2_isel[7:2]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pu_vchrg_div",\
},\
{0x66,\
0x0000,\
"reg_pu_ldo_11_dsleep",\
"reg_pu_ldo_11_dr",\
"reg_pu_ldo_11",\
"reg_lp_en_ldo_11_dsleep",\
"reg_lp_en_ldo_11_dr",\
"reg_lp_en_ldo_11",\
"reg_ldo_11_pulldown",\
"reg_ldo_11_bypass",\
"reg_ldo_11_vbit_dsleep[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x67,\
0x0000,\
"reg_pu_ldo_09_dsleep",\
"reg_pu_ldo_09_dr",\
"reg_pu_ldo_09",\
"reg_lp_en_ldo_09_dsleep",\
"reg_lp_en_ldo_09_dr",\
"reg_lp_en_ldo_09",\
" ",\
"reg_ldo_05_pulldown",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x68,\
0x0000,\
" ",\
"reg_ldo_05_vbit_rc[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_05_vbit_dsleep[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_05_vbit_normal[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x69,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_11_ramp_step[9:6]",\
" ",\
" ",\
" ",\
"reg_ldo_11_ramp_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x6a,\
0x0000,\
"reg_en_sw5_vusb33_dly",\
"reg_en_sw4_1p8_dly",\
"reg_en_sw3_1p8_dly",\
"reg_en_sw2_1p8_dly",\
"reg_en_sw1_1p8_dly",\
"reg_sw_dly_cnt_dr",\
"reg_en_sw_dly_cnt[9:3]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_en_sw_dly_sel[2:0]",\
" ",\
" ",\
},\
{0x6b,\
0x0000,\
"reg_en_sw6_vusb33_isel[15:12]",\
" ",\
" ",\
" ",\
"reg_en_sw6_vusb33_pull_down[11:10]",\
" ",\
"reg_en_sw6_vusb33",\
"reg_en_sw6_vusb33_dr",\
"reg_en_sw5_vusb33_isel[7:4]",\
" ",\
" ",\
" ",\
"reg_en_sw5_vusb33_pull_down[3:2]",\
" ",\
"reg_en_sw5_vusb33",\
"reg_en_sw5_vusb33_dr",\
},\
{0x6c,\
0x0000,\
"reg_en_sw6_vusb33_dly",\
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
"reg_en_sw7_1p8_dly",\
"reg_en_sw7_1p8",\
"reg_en_sw7_1p8_dr",\
"reg_en_sw7_1p8_pull_down[1:0]",\
" ",\
},\
{0x6d,\
0x0000,\
"reg_xo_32k_drv_sel[15:14]",\
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
"reg_pu_ldo_vmicb_dr",\
"reg_pu_ldo_vmica_dr",\
},\
{0x6f,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_xo_32k_capbit[8:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x70,\
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
"ap_active_only_sel",\
"ap_sleep_allow",\
"reg_rc_merge_mode",\
"rcsleep_mode_digi_dr",\
"rcsleep_mode_digi_reg",\
"rcsleep_allow",\
},\
{0x72,\
0x0000,\
" ",\
"reg_ldo_03_vbit_rc[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_03_vbit_normal[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_03_vbit_dsleep[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x74,\
0x0000,\
" ",\
" ",\
"reg_mic_biasa_vsel[13:9]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_dsleep_msk",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x75,\
0x0000,\
" ",\
" ",\
"reg_mic_biasb_vsel[13:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_dsleep[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x76,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_rc[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_normal[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x77,\
0x0000,\
" ",\
"reg_ldo_02_vbit_dsleep[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_02_vbit_rc[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_02_vbit_normal[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x79,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"rc_sleep_mode",\
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
{0x7a,\
0x0000,\
" ",\
"reg_clk_cap_32k_en",\
" ",\
" ",\
"reg_clk_cap_div_value[11:5]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_clk_cap_rc_sel",\
"reg_clk_cap_rc_gate_en",\
"reg_clk_cap_rc_gate_dr",\
"reg_clk_cap_osc_gate_en",\
"reg_clk_cap_osc_gate_dr",\
},\
{0x7b,\
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
"reg_ldo_02_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_02_ramp_en",\
},\
{0x7d,\
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
"reg_xo_32k_1hz_bypass[5:3]",\
" ",\
" ",\
"reg_aon_32k_xo_sel[2:0]",\
" ",\
" ",\
},\
{0x7e,\
0x0000,\
"reg_clk_32k_xo_div_1hz[15:0]",\
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
{0x82,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_08_pulldown",\
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
"reg_ldo_09_ramp_step[9:6]",\
" ",\
" ",\
" ",\
"reg_ldo_09_ramp_en",\
"reg_ldo_08_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_08_ramp_en",\
},\
{0x84,\
0x0000,\
" ",\
"reg_ldo_01_ramp_step[14:11]",\
" ",\
" ",\
" ",\
"reg_ldo_01_ramp_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_03_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_03_ramp_en",\
},\
{0x85,\
0x0000,\
" ",\
"reg_ldo_13_vbit_rc[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_13_vbit_dsleep[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_13_vbit_normal[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x88,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_06_vbit_rc[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_06_vbit_normal[5:0]",\
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
" ",\
" ",\
" ",\
" ",\
"reg_ldo_06_vbit_dsleep[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x8a,\
0x0000,\
"reg_ldo_09_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_09_vbit_normal[7:0]",\
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
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_09_vbit_dsleep[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x93,\
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
"reg_rcosc_48m_bypass_counter",\
"reg_rcosc_48m_counter_sel   [3:1]",\
" ",\
" ",\
" ",\
},\
{0x94,\
0x0000,\
" ",\
" ",\
" ",\
"reg_en_bg_aux_buf_dr",\
"bg_en_refresh_reg",\
"bg_en_refresh_dr",\
"bg_vbg_refresh_en_reg",\
"bg_vbg_refresh_en_dr",\
"bg_vref_gen_en_reg",\
"bg_vref_gen_en_dr",\
"bg_vref_sel_reg",\
"bg_vref_sel_dr",\
"bg_vref_refresh_en_reg",\
"bg_vref_refresh_en_dr",\
"bg_otp_en_reg",\
"bg_otp_en_dr",\
},\
{0x95,\
0x0000,\
"reserved_ana[15:0][15:0]",\
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
{0x97,\
0x0000,\
"avdd_2p7_sar_abort_source[15:12]",\
" ",\
" ",\
" ",\
"avdd_2p7_sar_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"avdd_2p7_bg_abort_source[7:4]",\
" ",\
" ",\
" ",\
"avdd_2p7_bg_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x98,\
0x0000,\
"buck_06_abort_source[15:12]",\
" ",\
" ",\
" ",\
"buck_06_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"buck_05_abort_source[7:4]",\
" ",\
" ",\
" ",\
"buck_05_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x99,\
0x0000,\
"buck_04_abort_source[15:12]",\
" ",\
" ",\
" ",\
"buck_04_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"buck_03_abort_source[7:4]",\
" ",\
" ",\
" ",\
"buck_03_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x9a,\
0x0000,\
"buck_02_abort_source[15:12]",\
" ",\
" ",\
" ",\
"buck_02_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"buck_01_abort_source[7:4]",\
" ",\
" ",\
" ",\
"buck_01_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x9b,\
0x0000,\
"ldo_02_abort_source[15:12]",\
" ",\
" ",\
" ",\
"ldo_02_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"ldo_01_abort_source[7:4]",\
" ",\
" ",\
" ",\
"ldo_01_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x9c,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"ldo_03_abort_source[7:4]",\
" ",\
" ",\
" ",\
"ldo_03_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x9d,\
0x0000,\
"ldo_06_abort_source[15:12]",\
" ",\
" ",\
" ",\
"ldo_06_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"ldo_05_abort_source[7:4]",\
" ",\
" ",\
" ",\
"ldo_05_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x9e,\
0x0000,\
"ldo_08_abort_source[15:12]",\
" ",\
" ",\
" ",\
"ldo_08_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"ldo_07_abort_source[7:4]",\
" ",\
" ",\
" ",\
"ldo_07_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x9f,\
0x0000,\
"ldo_10_abort_source[15:12]",\
" ",\
" ",\
" ",\
"ldo_10_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"ldo_09_abort_source[7:4]",\
" ",\
" ",\
" ",\
"ldo_09_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0xa0,\
0x0000,\
"ldo_12_abort_source[15:12]",\
" ",\
" ",\
" ",\
"ldo_12_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"ldo_11_abort_source[7:4]",\
" ",\
" ",\
" ",\
"ldo_11_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0xa1,\
0x0000,\
"ldo_14_abort_source[15:12]",\
" ",\
" ",\
" ",\
"ldo_14_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"ldo_13_abort_source[7:4]",\
" ",\
" ",\
" ",\
"ldo_13_reboot_cnt[3:0]",\
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
" ",\
"ldo_15_abort_source[7:4]",\
" ",\
" ",\
" ",\
"ldo_15_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0xa3,\
0x0000,\
"vmicb_abort_source[15:12]",\
" ",\
" ",\
" ",\
"vmicb_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"vmica_abort_source[7:4]",\
" ",\
" ",\
" ",\
"vmica_reboot_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0xa4,\
0x0000,\
"vbat_abort_source[15:12]",\
" ",\
" ",\
" ",\
"vbat_reboot_cnt[11:8]",\
" ",\
" ",\
" ",\
"vrtc_abort_source[7:4]",\
" ",\
" ",\
" ",\
"vrtc_reboot_cnt[3:0]",\
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
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"temp_intr_raw[1:0]",\
" ",\
},\
{0xa6,\
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
"temp_intr[1:0]",\
" ",\
},\
{0xa7,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"temp_data[11:0]",\
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
{0xa8,\
0x0000,\
" ",\
"reg_ldo_01_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xa9,\
0x0000,\
" ",\
"reg_ldo_01_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_oscp_func_en",\
"reg_ldo_01_ocp_en_dr",\
"reg_ldo_01_ocp_en_reg",\
},\
{0xaa,\
0x0000,\
"reg_ldo_01_break_time[15:14]",\
" ",\
"reg_ldo_01_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_01_reboot_trigger",\
"reg_ldo_01_reboot_trigger_dr",\
"reg_ldo_01_ldo_off_dr",\
"reg_ldo_01_ldo_off_reg",\
"reg_ldo_01_pmu_off_dr",\
"reg_ldo_01_pmu_off_reg",\
"reg_ldo_01_protec_cycle[3:2]",\
" ",\
"reg_ldo_01_handle_sel_pmu_off",\
"reg_ldo_01_hw_mode",\
},\
{0xab,\
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
"reg_ldo_01_abort_source_clr",\
"reg_ldo_01_intr_en",\
"reg_ldo_01_intr_msk",\
"reg_ldo_01_intr_clr",\
},\
{0xac,\
0x0000,\
" ",\
"reg_ldo_02_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_02_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_02_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xad,\
0x0000,\
" ",\
"reg_ldo_02_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_02_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_02_oscp_func_en",\
"reg_ldo_02_ocp_en_dr",\
"reg_ldo_02_ocp_en_reg",\
},\
{0xae,\
0x0000,\
"reg_ldo_02_break_time[15:14]",\
" ",\
"reg_ldo_02_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_02_reboot_trigger",\
"reg_ldo_02_reboot_trigger_dr",\
"reg_ldo_02_ldo_off_dr",\
"reg_ldo_02_ldo_off_reg",\
"reg_ldo_02_pmu_off_dr",\
"reg_ldo_02_pmu_off_reg",\
"reg_ldo_02_protec_cycle[3:2]",\
" ",\
"reg_ldo_02_handle_sel_pmu_off",\
"reg_ldo_02_hw_mode",\
},\
{0xaf,\
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
"reg_ldo_02_abort_source_clr",\
"reg_ldo_02_intr_en",\
"reg_ldo_02_intr_msk",\
"reg_ldo_02_intr_clr",\
},\
{0xb0,\
0x0000,\
"reg_gpio_p0_rpd[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p0_rpu[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xb1,\
0x0000,\
"reg_gpio_p0_data_out[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p0_oenb[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xb2,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p0_rx_en[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xb3,\
0x0000,\
"reg_gpio_p1_rpd[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p1_rpu[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xb4,\
0x0000,\
"reg_gpio_p1_data_out[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p1_oenb[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xb5,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p1_rx_en[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xb6,\
0x0000,\
"reg_gpio_p2_rpd[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p2_rpu[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xb7,\
0x0000,\
"reg_gpio_p2_data_out[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p2_oenb[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xb8,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p2_rx_en[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xb9,\
0x0000,\
"reg_gpio_p3_rpd[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p3_rpu[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xba,\
0x0000,\
"reg_gpio_p3_data_out[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p3_oenb[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xbb,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p3_rx_en[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xbc,\
0x0000,\
"gpio_p1_data_in[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p0_data_in[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xbd,\
0x0000,\
"gpio_p3_data_in[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p2_data_in[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xbe,\
0x0000,\
"reg_gpio_p0_intr_nedg_clr[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p0_intr_clr[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xbf,\
0x0000,\
"gpio_p0_intr_nedg_msk[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p0_intr_msk[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc0,\
0x0000,\
"reg_gpio_p0_lowlvl_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p0_edge_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc1,\
0x0000,\
"reg_gpio_p0_neg_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p0_pos_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc2,\
0x0000,\
"reg_gpio_p0_intr_en[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p0_db_bypass[7:0]",\
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
"reg_gpio_p1_db_target[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p0_db_target[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc4,\
0x0000,\
"reg_gpio_p1_intr_nedg_clr[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p1_intr_clr[7:0]",\
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
"gpio_p1_intr_nedg_msk[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p1_intr_msk[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc6,\
0x0000,\
"reg_gpio_p1_lowlvl_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p1_edge_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc7,\
0x0000,\
"reg_gpio_p1_neg_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p1_pos_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc8,\
0x0000,\
"reg_gpio_p1_intr_en[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p1_db_bypass[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xc9,\
0x0000,\
"reg_gpio_p2_intr_nedg_clr[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p2_intr_clr[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xca,\
0x0000,\
"gpio_p2_intr_nedg_msk[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p2_intr_msk[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xcb,\
0x0000,\
"reg_gpio_p2_lowlvl_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p2_edge_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xcc,\
0x0000,\
"reg_gpio_p2_neg_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p2_pos_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xcd,\
0x0000,\
"reg_gpio_p2_intr_en[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p2_db_bypass[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xce,\
0x0000,\
"reg_gpio_p3_db_target[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p2_db_target[7:0]",\
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
"reg_gpio_p3_intr_nedg_clr[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p3_intr_clr[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xd0,\
0x0000,\
"gpio_p3_intr_nedg_msk[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p3_intr_msk[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xd1,\
0x0000,\
"reg_gpio_p3_lowlvl_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p3_edge_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xd2,\
0x0000,\
"reg_gpio_p3_neg_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p3_pos_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xd3,\
0x0000,\
"reg_gpio_p3_intr_en[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p3_db_bypass[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xd4,\
0x0000,\
"reg_gpio_p0_ibit_sel[15:14]",\
" ",\
"reg_gpio_p1_ibit_sel[13:12]",\
" ",\
"reg_gpio_p2_ibit_sel[11:10]",\
" ",\
"reg_gpio_p3_ibit_sel[9:8]",\
" ",\
"reg_gpio_p4_ibit_sel[7:6]",\
" ",\
"reg_gpio_p5_ibit_sel[5:4]",\
" ",\
"reg_gpio_p6_ibit_sel[3:2]",\
" ",\
"reg_gpio_p7_ibit_sel[1:0]",\
" ",\
},\
{0xdc,\
0x0000,\
"gpio_p1_data_in_db[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p0_data_in_db[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xdd,\
0x0000,\
"gpio_p3_data_in_db[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p2_data_in_db[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xde,\
0x0000,\
"gpio_p1_intr_msked[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p0_intr_msked[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xdf,\
0x0000,\
"gpio_p3_intr_msked[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p2_intr_msked[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xe0,\
0x0000,\
"gpio_p1_nedg_intr_msked[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p0_nedg_intr_msked[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xe1,\
0x0000,\
"gpio_p3_nedg_intr_msked[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p2_nedg_intr_msked[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xe2,\
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
"gpio_60_intr",\
"gpio_60_nedg_intr",\
},\
{0xe3,\
0x0000,\
"gpio_p5_data_in_db[15:8]",\
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
"gpio_p4_data_in_db[3:0]",\
" ",\
" ",\
" ",\
},\
{0xe4,\
0x0000,\
"gpio_p7_data_in_db[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p6_data_in_db[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xe5,\
0x0000,\
"gpio_p5_intr_msked[15:8]",\
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
"gpio_p4_intr_msked[3:0]",\
" ",\
" ",\
" ",\
},\
{0xe6,\
0x0000,\
"gpio_p7_intr_msked[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p6_intr_msked[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xe7,\
0x0000,\
"gpio_p5_nedg_intr_msked[15:8]",\
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
"gpio_p4_nedg_intr_msked[3:0]",\
" ",\
" ",\
" ",\
},\
{0xe8,\
0x0000,\
"gpio_p7_nedg_intr_msked[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p6_nedg_intr_msked[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0xea,\
0x0000,\
" ",\
"reg_ldo_03_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_03_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_03_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xeb,\
0x0000,\
" ",\
"reg_ldo_03_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_03_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_03_oscp_func_en",\
"reg_ldo_03_ocp_en_dr",\
"reg_ldo_03_ocp_en_reg",\
},\
{0xec,\
0x0000,\
"reg_ldo_03_break_time[15:14]",\
" ",\
"reg_ldo_03_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_03_reboot_trigger",\
"reg_ldo_03_reboot_trigger_dr",\
"reg_ldo_03_ldo_off_dr",\
"reg_ldo_03_ldo_off_reg",\
"reg_ldo_03_pmu_off_dr",\
"reg_ldo_03_pmu_off_reg",\
"reg_ldo_03_protec_cycle[3:2]",\
" ",\
"reg_ldo_03_handle_sel_pmu_off",\
"reg_ldo_03_hw_mode",\
},\
{0xed,\
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
"reg_ldo_03_abort_source_clr",\
"reg_ldo_03_intr_en",\
"reg_ldo_03_intr_msk",\
"reg_ldo_03_intr_clr",\
},\
{0xee,\
0x0000,\
" ",\
"reg_ldo_05_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_05_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_05_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xef,\
0x0000,\
" ",\
"reg_ldo_05_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_05_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_05_oscp_func_en",\
"reg_ldo_05_ocp_en_dr",\
"reg_ldo_05_ocp_en_reg",\
},\
{0xf0,\
0x0000,\
"reg_ldo_05_break_time[15:14]",\
" ",\
"reg_ldo_05_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_05_reboot_trigger",\
"reg_ldo_05_reboot_trigger_dr",\
"reg_ldo_05_ldo_off_dr",\
"reg_ldo_05_ldo_off_reg",\
"reg_ldo_05_pmu_off_dr",\
"reg_ldo_05_pmu_off_reg",\
"reg_ldo_05_protec_cycle[3:2]",\
" ",\
"reg_ldo_05_handle_sel_pmu_off",\
"reg_ldo_05_hw_mode",\
},\
{0xf1,\
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
"reg_ldo_05_abort_source_clr",\
"reg_ldo_05_intr_en",\
"reg_ldo_05_intr_msk",\
"reg_ldo_05_intr_clr",\
},\
{0xf2,\
0x0000,\
" ",\
"reg_ldo_06_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_06_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_06_oscp_func_en",\
"reg_ldo_06_ocp_en_dr",\
"reg_ldo_06_ocp_en_reg",\
},\
{0xf3,\
0x0000,\
"reg_ldo_06_break_time[15:14]",\
" ",\
"reg_ldo_06_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_06_reboot_trigger",\
"reg_ldo_06_reboot_trigger_dr",\
"reg_ldo_06_ldo_off_dr",\
"reg_ldo_06_ldo_off_reg",\
"reg_ldo_06_pmu_off_dr",\
"reg_ldo_06_pmu_off_reg",\
"reg_ldo_06_protec_cycle[3:2]",\
" ",\
"reg_ldo_06_handle_sel_pmu_off",\
"reg_ldo_06_hw_mode",\
},\
{0xf4,\
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
"reg_ldo_06_abort_source_clr",\
"reg_ldo_06_intr_en",\
"reg_ldo_06_intr_msk",\
"reg_ldo_06_intr_clr",\
},\
{0xf5,\
0x0000,\
" ",\
"reg_ldo_07_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_07_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_07_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xf6,\
0x0000,\
" ",\
"reg_ldo_07_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_07_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_07_oscp_func_en",\
"reg_ldo_07_ocp_en_dr",\
"reg_ldo_07_ocp_en_reg",\
},\
{0xf7,\
0x0000,\
"reg_ldo_07_break_time[15:14]",\
" ",\
"reg_ldo_07_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_07_reboot_trigger",\
"reg_ldo_07_reboot_trigger_dr",\
"reg_ldo_07_ldo_off_dr",\
"reg_ldo_07_ldo_off_reg",\
"reg_ldo_07_pmu_off_dr",\
"reg_ldo_07_pmu_off_reg",\
"reg_ldo_07_protec_cycle[3:2]",\
" ",\
"reg_ldo_07_handle_sel_pmu_off",\
"reg_ldo_07_hw_mode",\
},\
{0xf8,\
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
"reg_ldo_07_abort_source_clr",\
"reg_ldo_07_intr_en",\
"reg_ldo_07_intr_msk",\
"reg_ldo_07_intr_clr",\
},\
{0xf9,\
0x0000,\
" ",\
"reg_ldo_08_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_08_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_08_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xfa,\
0x0000,\
" ",\
"reg_ldo_08_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_08_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_08_oscp_func_en",\
"reg_ldo_08_ocp_en_dr",\
"reg_ldo_08_ocp_en_reg",\
},\
{0xfb,\
0x0000,\
"reg_ldo_08_break_time[15:14]",\
" ",\
"reg_ldo_08_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_08_reboot_trigger",\
"reg_ldo_08_reboot_trigger_dr",\
"reg_ldo_08_ldo_off_dr",\
"reg_ldo_08_ldo_off_reg",\
"reg_ldo_08_pmu_off_dr",\
"reg_ldo_08_pmu_off_reg",\
"reg_ldo_08_protec_cycle[3:2]",\
" ",\
"reg_ldo_08_handle_sel_pmu_off",\
"reg_ldo_08_hw_mode",\
},\
{0xfc,\
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
"reg_ldo_08_abort_source_clr",\
"reg_ldo_08_intr_en",\
"reg_ldo_08_intr_msk",\
"reg_ldo_08_intr_clr",\
},\
{0xfd,\
0x0000,\
" ",\
"reg_ldo_09_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_09_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_09_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0xfe,\
0x0000,\
" ",\
"reg_ldo_09_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_09_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_09_oscp_func_en",\
"reg_ldo_09_ocp_en_dr",\
"reg_ldo_09_ocp_en_reg",\
},\
{0xff,\
0x0000,\
"reg_ldo_09_break_time[15:14]",\
" ",\
"reg_ldo_09_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_09_reboot_trigger",\
"reg_ldo_09_reboot_trigger_dr",\
"reg_ldo_09_ldo_off_dr",\
"reg_ldo_09_ldo_off_reg",\
"reg_ldo_09_pmu_off_dr",\
"reg_ldo_09_pmu_off_reg",\
"reg_ldo_09_protec_cycle[3:2]",\
" ",\
"reg_ldo_09_handle_sel_pmu_off",\
"reg_ldo_09_hw_mode",\
},\
{0x100,\
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
"reg_ldo_09_abort_source_clr",\
"reg_ldo_09_intr_en",\
"reg_ldo_09_intr_msk",\
"reg_ldo_09_intr_clr",\
},\
{0x101,\
0x0000,\
"reg_mic_biasa_ix2",\
"reg_mic_biasb_ix2",\
" ",\
" ",\
" ",\
" ",\
"reg_pu_ldo_dig_dsleep",\
" ",\
" ",\
"iptat_en",\
"reg_pu_avdd25_ana",\
" ",\
" ",\
" ",\
"reg_pu_vmem_delay_dr",\
"reg_pu_vmem_delay",\
},\
{0x102,\
0x0000,\
"reserved_pmu[15:0]",\
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
{0x103,\
0x0000,\
"r_pwm2_toggle[15:0]",\
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
{0x104,\
0x0000,\
"r_pwm3_toggle[15:0]",\
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
{0x105,\
0x0000,\
"reg_pwm2_st1[15:0]",\
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
{0x106,\
0x0000,\
"reg_pwm3_st1[15:0]",\
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
{0x107,\
0x0000,\
"subcnt_data2[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"subcnt_data3[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x108,\
0x0000,\
"tg_subcnt_d2_st[15:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pwm2_br_en",\
"tg_subcnt_d3_st[7:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pwm3_br_en",\
},\
{0x109,\
0x0000,\
"reg_led0_out",\
"reg_led1_out",\
"pwm_select_en[13:12]",\
" ",\
"pwm_select_inv[11:10]",\
" ",\
"reg_clk_pwm_div[9:5]",\
" ",\
" ",\
" ",\
" ",\
"dbg_cap_out[4:2]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x10a,\
0x0000,\
"reg_div_hw_reset[15:0]",\
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
{0x10b,\
0x0000,\
"reg_wdt_timer[15:0]",\
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
{0x10c,\
0x0000,\
"reg_hw_reset_time[15:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_hw_reset_en",\
"reg_wdt_reset_en",\
"reg_wdt_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x10e,\
0x0000,\
"pwm_clk_en[15:14]",\
" ",\
" ",\
" ",\
" ",\
"reg_pwm4_resetn",\
"reg_pwm3_resetn",\
"reg_pwm2_resetn",\
" ",\
" ",\
"pu_ldo_bg_dr",\
"pu_ldo_bg_reg",\
" ",\
" ",\
" ",\
" ",\
},\
{0x10f,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vbg_sel_dly_time[9:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_command_rst_dis",\
},\
{0x110,\
0x0000,\
"reg_gpio_i_sel",\
" ",\
"pmu_db_target1[13:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pmu_uart_dr1",\
"reg_pmu_uart_tx1",\
"reg_pmu_uart_oenb1",\
"reg_uart_leda_sel",\
" ",\
" ",\
},\
{0x111,\
0x0000,\
" ",\
" ",\
"pmu_db_target2[13:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pmu_uart_dr2",\
"reg_pmu_uart_tx2",\
"reg_pmu_uart_oenb2",\
"reg_uart_ledb_sel",\
" ",\
" ",\
},\
{0x112,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"power_up_mod10_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x113,\
0x0000,\
"power_up_mod8_cnt[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"power_up_mod7_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x114,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"power_up_mod1_cnt_dly[9:0]",\
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
{0x115,\
0x0000,\
" ",\
"reg_ldo_06_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_06_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_06_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x116,\
0x0000,\
"power_up_mod12_cnt[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"power_up_mod13_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x117,\
0x0000,\
"power_up_mod9_cnt[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"power_up_mod11_cnt[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x118,\
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
"reg_ldo_10_en_dr",\
"reg_ldo_10_en   ",\
},\
{0x119,\
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
"reg_ldo_07_en_dr",\
"reg_ldo_07_en   ",\
},\
{0x11a,\
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
"reg_ldo_06_bypass",\
"reg_ldo_07_bypass",\
"reg_ldo_08_bypass",\
"reg_ldo_09_bypass",\
"reg_lp_en_ldo_01_dsleep",\
"reg_pu_ldo_01_dsleep",\
},\
{0x11b,\
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
"reg_pu_main_lpo_dr",\
"reg_pu_main_lpo",\
},\
{0x11c,\
0x0000,\
"reg_ldo_08_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_08_vbit_normal[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x11d,\
0x0000,\
"reg_ldo_08_vbit_dsleep[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pu_ldo_08_dsleep",\
"reg_pu_ldo_08_dr",\
"reg_pu_ldo_08",\
"reg_lp_en_ldo_08_dsleep",\
"reg_lp_en_ldo_08_dr",\
"reg_lp_en_ldo_08",\
},\
{0x11f,\
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
"reg_lp_bias_sel_ldo_rc[6:4]",\
" ",\
" ",\
"reg_lp_bias_sel_ldo_dsleep[3:1]",\
" ",\
" ",\
"reg_lp_bias_sel_ramp_en",\
},\
{0x120,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_lp_bias_sel_ldo_normal[8:6]",\
" ",\
" ",\
"reg_lp_bias_sel_ramp_step[5:3]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x121,\
0x0000,\
"reg_lp_bias_res_sel_dr",\
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
{0x122,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_micbiasb_lp_enable",\
"reg_micbiasa_lp_enable",\
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
{0x123,\
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
"reg_led2_out",\
"pwm4_select_en",\
"pwm4_select_inv",\
"pwm4_clk_en",\
},\
{0x124,\
0x0000,\
"r_pwm4_toggle[15:0]",\
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
{0x125,\
0x0000,\
"reg_pwm4_st1[15:0]",\
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
{0x126,\
0x0000,\
"subcnt_data4[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"tg_subcnt_d4_st[7:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pwm4_br_en",\
},\
{0x127,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio3_pu",\
"gpio3_vsel[7:6]",\
" ",\
"gpio3_rx_en",\
"gpio3_rpu",\
"gpio3_rpd",\
"gpio3_oenb",\
"gpio3_ibit[1:0]",\
" ",\
},\
{0x128,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_command_rst_bit_width_tolerance[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x129,\
0x0000,\
"reg_pwm2_cut_off_st[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"subcnt_data2_off[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x12a,\
0x0000,\
" ",\
"reg_pwm2_min_light_ed[14:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pwm2_cut_off_ed[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x12b,\
0x0000,\
"reg_pwm3_cut_off_st[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"subcnt_data3_off[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x12c,\
0x0000,\
" ",\
"reg_pwm3_min_light_ed[14:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pwm3_cut_off_ed[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x12d,\
0x0000,\
"reg_pwm4_cut_off_st[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"subcnt_data4_off[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x12e,\
0x0000,\
" ",\
"reg_pwm4_min_light_ed[14:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pwm4_cut_off_ed[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x12f,\
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
"reg_pwm4_br_on_keep",\
"reg_pwm4_br_off_keep",\
"reg_pwm3_br_on_keep",\
"reg_pwm3_br_off_keep",\
"reg_pwm2_br_on_keep",\
"reg_pwm2_br_off_keep",\
},\
{0x130,\
0x0000,\
" ",\
" ",\
"reg_buck_02_vcomp_lp_sel",\
" ",\
"reg_buck_02_threshold_sel",\
"reg_buck_02_subharmonic_sel",\
" ",\
"reg_buck_02_cal_deltav[8:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_logic_sel",\
},\
{0x131,\
0x0000,\
" ",\
" ",\
"reg_buck_04_vcomp_lp_sel",\
" ",\
"reg_buck_04_threshold_sel",\
"reg_buck_04_subharmonic_sel",\
" ",\
"reg_buck_04_cal_deltav[8:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_logic_sel",\
},\
{0x132,\
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
"reg_buck_06_vref_sel_dsleep[5:4]",\
" ",\
"reg_buck_06_vref_sel_rc[3:2]",\
" ",\
"reg_buck_06_vref_sel_normal[1:0]",\
" ",\
},\
{0x133,\
0x0000,\
" ",\
"reg_ldo_10_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_10_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_10_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x134,\
0x0000,\
" ",\
"reg_ldo_10_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_10_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_10_oscp_func_en",\
"reg_ldo_10_ocp_en_dr",\
"reg_ldo_10_ocp_en_reg",\
},\
{0x135,\
0x0000,\
"reg_ldo_10_break_time[15:14]",\
" ",\
"reg_ldo_10_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_10_reboot_trigger",\
"reg_ldo_10_reboot_trigger_dr",\
"reg_ldo_10_ldo_off_dr",\
"reg_ldo_10_ldo_off_reg",\
"reg_ldo_10_pmu_off_dr",\
"reg_ldo_10_pmu_off_reg",\
"reg_ldo_10_protec_cycle[3:2]",\
" ",\
"reg_ldo_10_handle_sel_pmu_off",\
"reg_ldo_10_hw_mode",\
},\
{0x136,\
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
"reg_ldo_10_abort_source_clr",\
"reg_ldo_10_intr_en",\
"reg_ldo_10_intr_msk",\
"reg_ldo_10_intr_clr",\
},\
{0x139,\
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
"reg_buck_01_soft_start_dr",\
"reg_buck_01_soft_start",\
"reg_buck_01_soft_start_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x13b,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_ton_bit_normal[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_01_ton_bit_dsleep[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_01_ton_bit_rc[3:0]",\
" ",\
" ",\
" ",\
},\
{0x13c,\
0x0000,\
"reg_buck_01_force_mode_normal",\
"reg_buck_01_ulp_mode_sel_normal",\
"reg_buck_01_vcomp_vsel_normal",\
"reg_buck_01_reg_mode_normal",\
"reg_buck_01_vcomp_1u_normal",\
"reg_buck_01_ulp_res_normal",\
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
{0x13d,\
0x0000,\
"reg_buck_01_force_mode_dsleep",\
"reg_buck_01_ulp_mode_sel_dsleep",\
"reg_buck_01_vcomp_vsel_dsleep",\
"reg_buck_01_reg_mode_dsleep",\
"reg_buck_01_vcomp_1u_dsleep",\
"reg_buck_01_ulp_res_dsleep",\
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
{0x13e,\
0x0000,\
"reg_buck_01_force_mode_rc",\
"reg_buck_01_ulp_mode_sel_rc",\
"reg_buck_01_vcomp_vsel_rc",\
"reg_buck_01_reg_mode_rc",\
"reg_buck_01_vcomp_1u_rc",\
"reg_buck_01_ulp_res_rc",\
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
{0x140,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_en_zcd_cal",\
"reg_buck_02_anti_res_disable",\
"reg_buck_02_zcd_cap_bit[7:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x141,\
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
"reg_buck_02_vref_sel_normal[4:3]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x142,\
0x0000,\
"reg_buck_02_force_reg_bypass",\
" ",\
"reg_buck_02_vcomp_ix2_hp[13:12]",\
" ",\
"reg_buck_02_test_bit[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_02_clk_32k_en",\
"reg_buck_02_nlimit_bit[6:4]",\
" ",\
" ",\
"reg_buck_02_plimit_bit[3:1]",\
" ",\
" ",\
" ",\
},\
{0x143,\
0x0000,\
"reg_buck_02_reset_zcd",\
"reg_buck_02_en_ulp_protect_time",\
"reg_buck_02_vcomp_ix2",\
" ",\
"reg_buck_02_counter_sel_mode",\
"reg_buck_02_err_ix2",\
"reg_buck_02_force_vcomp_normal",\
" ",\
" ",\
"reg_buck_02_vcomp_lp[6:4]",\
" ",\
" ",\
"reg_buck_02_pd_clamph",\
"reg_buck_02_pd_clampl",\
"reg_buck_02_protect_time_50u",\
"reg_buck_02_ulp_pulse_en",\
},\
{0x144,\
0x0000,\
"reg_buck_02_reserved[15:0]",\
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
{0x145,\
0x0000,\
"reg_buck_02_pull_down",\
"reg_buck_02_soft_start_dr",\
"reg_buck_02_soft_start",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_ramp_step[8:4]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_ramp_en  ",\
"reg_buck_02_dsleep_msk",\
"reg_pu_buck_02_dr     ",\
"reg_pu_buck_02        ",\
},\
{0x146,\
0x0000,\
"reg_buck_02_force_mode_normal",\
"reg_buck_02_ulp_mode_sel_normal",\
"reg_buck_02_vcomp_vsel_normal",\
"reg_buck_02_reg_mode_normal",\
"reg_buck_02_vcomp_1u_normal",\
"reg_buck_02_ulp_res_normal",\
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
{0x147,\
0x0000,\
"reg_buck_02_force_mode_dsleep",\
"reg_buck_02_ulp_mode_sel_dsleep",\
"reg_buck_02_vcomp_vsel_dsleep",\
"reg_buck_02_reg_mode_dsleep",\
"reg_buck_02_vcomp_1u_dsleep",\
"reg_buck_02_ulp_res_dsleep",\
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
{0x148,\
0x0000,\
"reg_buck_02_force_mode_rc",\
"reg_buck_02_ulp_mode_sel_rc",\
"reg_buck_02_vcomp_vsel_rc",\
"reg_buck_02_reg_mode_rc",\
"reg_buck_02_vcomp_1u_rc",\
"reg_buck_02_ulp_res_rc",\
"reg_buck_02_force_ulp_res",\
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
{0x149,\
0x0000,\
"reg_buck_02_ton_bit_normal[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_02_ton_bit_dsleep[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_02_ton_bit_rc[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_02_soft_start_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x14a,\
0x0000,\
" ",\
"reg_buck_02_force_vcomp_10u_normal",\
"reg_buck_02_force_vcomp_10u_dsleep",\
"reg_buck_02_force_vcomp_10u_rc",\
"reg_buck_02_vref_sel_dsleep[11:10]",\
" ",\
"reg_buck_02_vref_sel_rc[9:8]",\
" ",\
"reg_buck_02_vbit_dsleep[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x14b,\
0x0000,\
"reg_buck_02_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_vbit_normal[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x14c,\
0x0000,\
" ",\
" ",\
"reg_buck_02_sw_en_dly_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_sw_en_dly_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x14d,\
0x0000,\
"reg_buck_02_bg_en_dr",\
"reg_buck_02_bg_en",\
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
{0x14e,\
0x0000,\
"reg_buck_02_sw_en_dr",\
"reg_buck_02_sw_en",\
"reg_buck_02_bg_hi2sw_hi_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_bg_hi2sw_hi_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x14f,\
0x0000,\
" ",\
" ",\
"dig_buck_02_bg_en",\
"dig_buck_02_sw_en",\
" ",\
"reg_buck_02_bg_low2sw_low_fast_cnt[10:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_bg_low2sw_low_slow_cnt[3:2]",\
" ",\
" ",\
" ",\
},\
{0x150,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_en_zcd_cal",\
"reg_buck_04_anti_res_disable",\
"reg_buck_04_zcd_cap_bit[7:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x151,\
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
"reg_buck_04_vref_sel_normal[4:3]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x152,\
0x0000,\
"reg_buck_04_force_reg_bypass",\
" ",\
"reg_buck_04_vcomp_ix2_hp[13:12]",\
" ",\
"reg_buck_04_test_bit[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_04_clk_32k_en",\
"reg_buck_04_nlimit_bit[6:4]",\
" ",\
" ",\
"reg_buck_04_plimit_bit[3:1]",\
" ",\
" ",\
" ",\
},\
{0x153,\
0x0000,\
"reg_buck_04_reset_zcd",\
"reg_buck_04_en_ulp_protect_time",\
"reg_buck_04_vcomp_ix2",\
" ",\
"reg_buck_04_counter_sel_mode",\
"reg_buck_04_err_ix2",\
"reg_buck_04_force_vcomp_normal",\
" ",\
" ",\
"reg_buck_04_vcomp_lp[6:4]",\
" ",\
" ",\
"reg_buck_04_pd_clamph",\
"reg_buck_04_pd_clampl",\
"reg_buck_04_protect_time_50u",\
"reg_buck_04_ulp_pulse_en",\
},\
{0x154,\
0x0000,\
"reg_buck_04_reserved[15:0]",\
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
{0x155,\
0x0000,\
"reg_buck_04_pull_down",\
"reg_buck_04_soft_start_dr",\
"reg_buck_04_soft_start",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_ramp_step[8:4]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_ramp_en  ",\
"reg_buck_04_dsleep_msk",\
"reg_pu_buck_04_dr     ",\
"reg_pu_buck_04        ",\
},\
{0x156,\
0x0000,\
"reg_buck_04_force_mode_normal",\
"reg_buck_04_ulp_mode_sel_normal",\
"reg_buck_04_vcomp_vsel_normal",\
"reg_buck_04_reg_mode_normal",\
"reg_buck_04_vcomp_1u_normal",\
"reg_buck_04_ulp_res_normal",\
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
{0x157,\
0x0000,\
"reg_buck_04_force_mode_dsleep",\
"reg_buck_04_ulp_mode_sel_dsleep",\
"reg_buck_04_vcomp_vsel_dsleep",\
"reg_buck_04_reg_mode_dsleep",\
"reg_buck_04_vcomp_1u_dsleep",\
"reg_buck_04_ulp_res_dsleep",\
" ",\
" ",\
"reg_buck_04_vbit_dsleep[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x158,\
0x0000,\
"reg_buck_04_force_mode_rc",\
"reg_buck_04_ulp_mode_sel_rc",\
"reg_buck_04_vcomp_vsel_rc",\
"reg_buck_04_reg_mode_rc",\
"reg_buck_04_vcomp_1u_rc",\
"reg_buck_04_ulp_res_rc",\
"reg_buck_04_force_ulp_res",\
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
{0x159,\
0x0000,\
"reg_buck_04_ton_bit_normal[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_04_ton_bit_dsleep[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_04_ton_bit_rc[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_04_soft_start_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x15a,\
0x0000,\
" ",\
"reg_buck_04_force_vcomp_10u_normal",\
"reg_buck_04_force_vcomp_10u_dsleep",\
"reg_buck_04_force_vcomp_10u_rc",\
"reg_buck_04_vref_sel_dsleep[11:10]",\
" ",\
"reg_buck_04_vref_sel_rc[9:8]",\
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
{0x15b,\
0x0000,\
"reg_buck_04_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_vbit_normal[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x15c,\
0x0000,\
" ",\
" ",\
"reg_buck_04_sw_en_dly_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_sw_en_dly_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x15d,\
0x0000,\
"reg_buck_04_bg_en_dr",\
"reg_buck_04_bg_en",\
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
{0x15e,\
0x0000,\
"reg_buck_04_sw_en_dr",\
"reg_buck_04_sw_en",\
"reg_buck_04_bg_hi2sw_hi_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_bg_hi2sw_hi_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x15f,\
0x0000,\
" ",\
" ",\
"dig_buck_04_bg_en",\
"dig_buck_04_sw_en",\
" ",\
"reg_buck_04_bg_low2sw_low_fast_cnt[10:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_bg_low2sw_low_slow_cnt[3:2]",\
" ",\
" ",\
" ",\
},\
{0x160,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_abort_time[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_oscp_func_en",\
" ",\
" ",\
},\
{0x161,\
0x0000,\
" ",\
"reg_buck_02_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x162,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_abort_time[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_oscp_func_en",\
" ",\
" ",\
},\
{0x163,\
0x0000,\
" ",\
"reg_buck_04_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x164,\
0x0000,\
" ",\
" ",\
"sleep_auto_refresh_msk",\
"reg_refresh_mode_en",\
"reg_refresh_cycle_cnt[11:0]",\
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
{0x165,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_refresh_on_cnt[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_refresh_on_dly_cnt[4:2]",\
" ",\
" ",\
"reg_refresh_off_dly_cnt[1:0]",\
" ",\
},\
{0x166,\
0x0000,\
" ",\
"reg_vbg_refresh_sel[14:13]",\
" ",\
"reg_refresh_bg",\
"reg_refresh_bg_dr",\
"reg_refresh_d1",\
"reg_refresh_d1_dr",\
"reg_refresh_d2",\
"reg_refresh_d2_dr",\
"reg_refresh_d3",\
"reg_refresh_d3_dr",\
"reg_refresh_d4",\
"reg_refresh_d4_dr",\
" ",\
" ",\
" ",\
},\
{0x167,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_refresh_d1_dly[11:8]",\
" ",\
" ",\
" ",\
"reg_refresh_d2_dly[7:4]",\
" ",\
" ",\
" ",\
"reg_refresh_d3_dly[3:0]",\
" ",\
" ",\
" ",\
},\
{0x168,\
0x0000,\
" ",\
"reg_buck_01_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x169,\
0x0000,\
" ",\
"reg_buck_01_low_temp_offset[14:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_abort_time[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_oscp_func_en",\
" ",\
" ",\
},\
{0x16a,\
0x0000,\
"reg_buck_01_break_time[15:14]",\
" ",\
"reg_buck_01_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_buck_01_reboot_trigger",\
"reg_buck_01_reboot_trigger_dr",\
"reg_buck_01_dcdc_off_dr",\
"reg_buck_01_dcdc_off_reg",\
"reg_buck_01_pmu_off_dr",\
"reg_buck_01_pmu_off_reg",\
"reg_buck_01_protec_cycle[3:2]",\
" ",\
"reg_buck_01_handle_sel_pmu_off",\
"reg_buck_01_hw_mode",\
},\
{0x16b,\
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
"reg_buck_01_abort_source_clr",\
"reg_buck_01_intr_en",\
"reg_buck_01_intr_msk",\
"reg_buck_01_intr_clr",\
},\
{0x16c,\
0x0000,\
" ",\
"reg_buck_06_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x16d,\
0x0000,\
" ",\
"reg_buck_06_low_temp_offset[14:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_abort_time[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_oscp_func_en",\
" ",\
" ",\
},\
{0x16e,\
0x0000,\
"reg_buck_06_break_time[15:14]",\
" ",\
"reg_buck_06_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_buck_06_reboot_trigger",\
"reg_buck_06_reboot_trigger_dr",\
"reg_buck_06_dcdc_off_dr",\
"reg_buck_06_dcdc_off_reg",\
"reg_buck_06_pmu_off_dr",\
"reg_buck_06_pmu_off_reg",\
"reg_buck_06_protec_cycle[3:2]",\
" ",\
"reg_buck_06_handle_sel_pmu_off",\
"reg_buck_06_hw_mode",\
},\
{0x16f,\
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
"reg_buck_06_abort_source_clr",\
"reg_buck_06_intr_en",\
"reg_buck_06_intr_msk",\
"reg_buck_06_intr_clr",\
},\
{0x170,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan8[11:0]",\
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
{0x171,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan9[11:0]",\
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
{0x172,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan10[11:0]",\
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
{0x173,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan11[11:0]",\
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
{0x174,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan12[11:0]",\
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
{0x175,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"data_chan13[11:0]",\
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
{0x176,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_ramp_en",\
"reg_buck_01_ramp_step[10:6]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_ramp_en",\
"reg_buck_06_ramp_step[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x178,\
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
"reg_clk_rtc_sel_xo",\
"rtc_load",\
},\
{0x179,\
0x0000,\
"rtc_time_load_value[15:0][15:0]",\
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
{0x17a,\
0x0000,\
"rtc_time_load_value[31:16][15:0]",\
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
{0x17b,\
0x0000,\
"rtc_date_load_value[15:0][15:0]",\
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
{0x17c,\
0x0000,\
"rtc_date_load_value[31:16][15:0]",\
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
{0x17d,\
0x0000,\
"rtc_time_value[15:0][15:0]",\
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
{0x17e,\
0x0000,\
"rtc_time_value[31:16][15:0]",\
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
{0x17f,\
0x0000,\
"rtc_date_value[15:0][15:0]",\
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
{0x180,\
0x0000,\
"rtc_date_value[31:16][15:0]",\
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
{0x181,\
0x0000,\
" ",\
" ",\
"reg_vref_ov_sel0[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_ov_sel1[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x182,\
0x0000,\
" ",\
" ",\
"reg_vref_ov_sel2[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_ov_sel3[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x183,\
0x0000,\
" ",\
" ",\
"reg_vref_ov_sel4[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_ov_sel5[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x184,\
0x0000,\
" ",\
" ",\
"reg_vref_ov_sel6[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_ov_sel7[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x185,\
0x0000,\
" ",\
" ",\
"reg_vref_ov_sel8[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_ov_sel9[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x186,\
0x0000,\
" ",\
" ",\
"reg_vref_ov_sela[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel0[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x187,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel1[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel2[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x188,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel3[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel4[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x189,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel5[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel6[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x18a,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel7[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel8[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x18b,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel9[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sela[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x18c,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_selb[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_selc[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x18d,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_seld[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sele[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x18e,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_self[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_en_ov_pu_msk",\
"reg_en_uv_pu_msk",\
"reg_en_ov_det_dr",\
"reg_en_ov_det_reg",\
"reg_en_uv_det_dr",\
"reg_en_uv_det_reg",\
},\
{0x18f,\
0x0000,\
" ",\
"reg_vdet_bias_sel[14:11]",\
" ",\
" ",\
" ",\
"reg_ov_det_cnt[10:6]",\
" ",\
" ",\
" ",\
" ",\
"reg_uv_det_cnt[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x190,\
0x0000,\
"reg_ov_msk[15:0]",\
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
{0x191,\
0x0000,\
"reg_uv_msk[15:0][15:0]",\
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
{0x192,\
0x0000,\
"reg_en_ov_det",\
"reg_en_uv_det",\
" ",\
" ",\
" ",\
"reg_vdet_ov_chan_sel_dr",\
"reg_vdet_ov_chan_sel_reg[9:6]",\
" ",\
" ",\
" ",\
"reg_vdet_uv_chan_sel_dr",\
"reg_vdet_uv_chan_sel_reg[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x193,\
0x0000,\
"reg_vol_det_cycle[15:11]",\
" ",\
" ",\
" ",\
" ",\
"reg_vdet_vref_sel_dr",\
"reg_vdet_vref_sel_reg[9:3]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_wait_switch[2:0]",\
" ",\
" ",\
},\
{0x194,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"clk_iptat_div_value[9:5]",\
" ",\
" ",\
" ",\
" ",\
"clk_iptat_en",\
"reg_bg_notch_lpf_low_bw",\
"reg_bg_r_temp[2:0]",\
" ",\
" ",\
},\
{0x196,\
0x0000,\
"reserved_dig[15:0]",\
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
{0x197,\
0x0000,\
" ",\
" ",\
" ",\
"reg_clk_ramp_en",\
"reg_clk_ramp_only_bypass",\
"reg_clk_ramp_only_div[10:6]",\
" ",\
" ",\
" ",\
" ",\
"reg_ramp_div_bypass",\
"reg_clk_ramp_bias_div        [4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x198,\
0x0000,\
" ",\
" ",\
"reg_low_temp_ramp_fast_en",\
"reg_ramp_bias_fast_msk",\
"reg_clk_ramp_div        [11:7]",\
" ",\
" ",\
" ",\
" ",\
"reg_clk_ramp_rc_gate_en ",\
"reg_ramp_clk_time  [5:2]",\
" ",\
" ",\
" ",\
"reg_ramp_fast_en_dr",\
"reg_ramp_fast_en",\
},\
{0x199,\
0x0000,\
" ",\
" ",\
"reg_clk_rc_ori_gate_cnt[13:9]",\
" ",\
" ",\
" ",\
" ",\
"reg_rc_clk_ori_dly_sel",\
"reg_clk_ramp_vote_div[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_clk_ramp_vote_div_bypass",\
"reg_clk_ramp_vote_sel",\
"reg_clk_osc_ramp_vote_en",\
},\
{0x1a1,\
0x0000,\
"reg_vmica_abort_source_clr",\
"reg_vmica_handle_sel_pmu_off",\
"reg_vmica_hw_mode",\
"reg_vmica_intr_clr",\
"reg_vmica_intr_en",\
"reg_vmica_intr_msk",\
"reg_vmica_ldo_off_dr",\
"reg_vmica_ldo_off_reg",\
"reg_vmica_pmu_off_dr",\
"reg_vmica_pmu_off_reg",\
"reg_vmica_reboot_cycle[5:2]",\
" ",\
" ",\
" ",\
"reg_vmica_break_time[1:0]",\
" ",\
},\
{0x1a2,\
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
"reg_vmica_reboot_trigger",\
"reg_vmica_reboot_trigger_dr",\
},\
{0x1a3,\
0x0000,\
"reg_vmicb_abort_source_clr",\
"reg_vmicb_handle_sel_pmu_off",\
"reg_vmicb_hw_mode",\
"reg_vmicb_intr_clr",\
"reg_vmicb_intr_en",\
"reg_vmicb_intr_msk",\
"reg_vmicb_ldo_off_dr",\
"reg_vmicb_ldo_off_reg",\
"reg_vmicb_pmu_off_dr",\
"reg_vmicb_pmu_off_reg",\
"reg_vmicb_reboot_cycle[5:2]",\
" ",\
" ",\
" ",\
"reg_vmicb_break_time[1:0]",\
" ",\
},\
{0x1a4,\
0x0000,\
"reg_reboot_time_out[15:8]",\
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
"reg_vmicb_reboot_trigger",\
"reg_vmicb_reboot_trigger_dr",\
},\
{0x1a5,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vdet_cal_en",\
"reg_vdet_cal_osp[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_vdet_cal_osn[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1a6,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_data_out[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1a7,\
0x0000,\
"reg_efuse_rden_dr     ",\
"reg_efuse_pu_avdd_dr  ",\
"reg_efuse_e09v_dr     ",\
"reg_efuse_e18v_dr     ",\
"reg_efuse_pgmen_dr    ",\
"reg_efuse_aen_dr      ",\
"reg_efuse_rden        ",\
"reg_efuse_pu_avdd     ",\
"reg_efuse_e09v        ",\
"reg_efuse_e18v        ",\
"reg_efuse_pgmen       ",\
"reg_efuse_aen         ",\
" ",\
"reg_efuse_data_out_dr",\
" ",\
" ",\
},\
{0x1a8,\
0x0000,\
"reg_efuse_address[15:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_strobe_trigger",\
"reg_efuse_turn_on",\
"reg_efuse_clk_en",\
"reg_efuse_read_mode",\
"reg_efuse_pgm_mode",\
"reg_efuse_pgm_read_sel",\
},\
{0x1a9,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_e18v_en_time[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_addr_en_time[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1aa,\
0x0000,\
" ",\
"reg_efuse_strobe_pre_time[14:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_pgm_strobe_time[8:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1ab,\
0x0000,\
" ",\
"reg_efuse_read_strobe_time[14:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_pgm_cold_time[8:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1ac,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_read_cold_time[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_e18v_dis_time[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1ad,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_e09v_dis_time[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_avdd_dis_time[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1ae,\
0x0000,\
" ",\
"reg_efuse_e09v_en_time[14:9]",\
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
" ",\
" ",\
" ",\
},\
{0x1af,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"efuse_fsm[11:8]",\
" ",\
" ",\
" ",\
"efuse_data_out[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1b0,\
0x0000,\
" ",\
" ",\
"reg_efuse_auto_read",\
"reg_base_addr[12:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_addr_inc[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1b1,\
0x0000,\
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
"reg_sq_time[3:0]",\
" ",\
" ",\
" ",\
},\
{0x1b2,\
0x0000,\
" ",\
" ",\
" ",\
"reg_efuse_power_on_read_address[12:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_power_on_read_inc[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1b3,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_clk_efuse_div_bypass",\
"reg_clk_efuse_div[8:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_clk_fast_sel",\
"reg_clk_efuse_rc_gate_en",\
"reg_clk_efuse_osc_gate_en",\
},\
{0x1bd,\
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
"bg_core_en_sleep_msk",\
"bg_vbg_sel_sleep_msk",\
"bg_constant_gm_bias_sleep_msk",\
"bg_vtoi_en_sleep_msk",\
"bg_vref_gen_en_sleep_msk",\
"bg_vref_sel_sleep_msk",\
"bg_opt_en_sleep_msk",\
},\
{0x1be,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"abort_source_clr",\
"pmu_ldo_on_source_clr",\
"abort_source[5:3]",\
" ",\
" ",\
"pmu_ldo_on_source[2:0]",\
" ",\
" ",\
},\
{0x1c6,\
0x0000,\
" ",\
" ",\
"reg_pu_rc6m_msk",\
"reg_2m_open_cnt[12:5]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_2m_ramp_gate_msk[4:1]",\
" ",\
" ",\
" ",\
"reg_ramp_mode_sel",\
},\
{0x1c7,\
0x0000,\
" ",\
" ",\
" ",\
"reg_wake_gpio_dual_edge_sel",\
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
{0x1ca,\
0x0000,\
"reg_buck_02_abort_source_clr",\
"reg_buck_02_handle_sel_pmu_off",\
"reg_buck_02_hw_mode",\
"reg_buck_02_intr_clr",\
"reg_buck_02_intr_en",\
"reg_buck_02_intr_msk",\
"reg_buck_02_dcdc_off_dr",\
"reg_buck_02_dcdc_off_reg",\
"reg_buck_02_pmu_off_dr",\
"reg_buck_02_pmu_off_reg",\
"reg_buck_02_reboot_cycle[5:2]",\
" ",\
" ",\
" ",\
"reg_buck_02_break_time[1:0]",\
" ",\
},\
{0x1cb,\
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
"reg_buck_02_protec_cycle[3:2]",\
" ",\
"reg_buck_02_reboot_trigger",\
"reg_buck_02_reboot_trigger_dr",\
},\
{0x1cc,\
0x0000,\
"reg_buck_03_abort_source_clr",\
"reg_buck_03_handle_sel_pmu_off",\
"reg_buck_03_hw_mode",\
"reg_buck_03_intr_clr",\
"reg_buck_03_intr_en",\
"reg_buck_03_intr_msk",\
"reg_buck_03_dcdc_off_dr",\
"reg_buck_03_dcdc_off_reg",\
"reg_buck_03_pmu_off_dr",\
"reg_buck_03_pmu_off_reg",\
"reg_buck_03_reboot_cycle[5:2]",\
" ",\
" ",\
" ",\
"reg_buck_03_break_time[1:0]",\
" ",\
},\
{0x1cd,\
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
"reg_buck_03_protec_cycle[3:2]",\
" ",\
"reg_buck_03_reboot_trigger",\
"reg_buck_03_reboot_trigger_dr",\
},\
{0x1ce,\
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
"reg_buck_04_edge_pconp_rc[5:3]",\
" ",\
" ",\
"reg_buck_04_edge_pconp_dsleep[2:0]",\
" ",\
" ",\
},\
{0x1cf,\
0x0000,\
" ",\
"reg_buck_04_edge_pconp_normal[14:12]",\
" ",\
" ",\
"reg_buck_04_edge_pconn_rc[11:9]",\
" ",\
" ",\
"reg_buck_04_edge_pconn_dsleep[8:6]",\
" ",\
" ",\
"reg_buck_04_edge_pconn_normal[5:3]",\
" ",\
" ",\
"reg_buck_04_edge_nconp_rc[2:0]",\
" ",\
" ",\
},\
{0x1d0,\
0x0000,\
" ",\
"reg_buck_04_edge_nconp_dsleep[14:12]",\
" ",\
" ",\
"reg_buck_04_edge_nconp_normal[11:9]",\
" ",\
" ",\
"reg_buck_04_edge_nconn_rc[8:6]",\
" ",\
" ",\
"reg_buck_04_edge_nconn_dsleep[5:3]",\
" ",\
" ",\
"reg_buck_04_edge_nconn_normal[2:0]",\
" ",\
" ",\
},\
{0x1d1,\
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
"reg_buck_01_edge_pconp_rc[5:3]",\
" ",\
" ",\
"reg_buck_01_edge_pconp_dsleep[2:0]",\
" ",\
" ",\
},\
{0x1d2,\
0x0000,\
" ",\
"reg_buck_01_edge_pconp_normal[14:12]",\
" ",\
" ",\
"reg_buck_01_edge_pconn_rc[11:9]",\
" ",\
" ",\
"reg_buck_01_edge_pconn_dsleep[8:6]",\
" ",\
" ",\
"reg_buck_01_edge_pconn_normal[5:3]",\
" ",\
" ",\
"reg_buck_01_edge_nconp_rc[2:0]",\
" ",\
" ",\
},\
{0x1d3,\
0x0000,\
" ",\
"reg_buck_01_edge_nconp_dsleep[14:12]",\
" ",\
" ",\
"reg_buck_01_edge_nconp_normal[11:9]",\
" ",\
" ",\
"reg_buck_01_edge_nconn_rc[8:6]",\
" ",\
" ",\
"reg_buck_01_edge_nconn_dsleep[5:3]",\
" ",\
" ",\
"reg_buck_01_edge_nconn_normal[2:0]",\
" ",\
" ",\
},\
{0x1d5,\
0x0000,\
" ",\
"reg_buck_05_soft_start_dr",\
"reg_buck_05_soft_start",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_ramp_step[8:4]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_ramp_en  ",\
"reg_buck_05_dsleep_msk",\
"reg_pu_buck_05_dr     ",\
"reg_pu_buck_05",\
},\
{0x1d6,\
0x0000,\
"reg_buck_05_force_mode_normal",\
"reg_buck_05_ulp_mode_sel_normal",\
"reg_buck_05_vcomp_vsel_normal",\
"reg_buck_05_reg_mode_normal",\
"reg_buck_05_vcomp_1u_normal",\
"reg_buck_05_ulp_res_normal",\
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
{0x1d7,\
0x0000,\
"reg_buck_05_force_mode_dsleep",\
"reg_buck_05_ulp_mode_sel_dsleep",\
"reg_buck_05_vcomp_vsel_dsleep",\
"reg_buck_05_reg_mode_dsleep",\
"reg_buck_05_vcomp_1u_dsleep",\
"reg_buck_05_ulp_res_dsleep",\
" ",\
" ",\
"reg_buck_05_vbit_dsleep[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1d8,\
0x0000,\
"reg_buck_05_force_mode_rc",\
"reg_buck_05_ulp_mode_sel_rc",\
"reg_buck_05_vcomp_vsel_rc",\
"reg_buck_05_reg_mode_rc",\
"reg_buck_05_vcomp_1u_rc",\
"reg_buck_05_ulp_res_rc",\
"reg_buck_05_force_ulp_res",\
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
{0x1d9,\
0x0000,\
"reg_buck_05_ton_bit_normal[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_05_ton_bit_dsleep[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_05_ton_bit_rc[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_05_soft_start_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x1da,\
0x0000,\
" ",\
"reg_buck_05_force_vcomp_10u_normal",\
"reg_buck_05_force_vcomp_10u_dsleep",\
"reg_buck_05_force_vcomp_10u_rc",\
"reg_buck_05_vref_sel_dsleep[11:10]",\
" ",\
"reg_buck_05_vref_sel_rc[9:8]",\
" ",\
"reg_buck_05_vref_sel_normal[7:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1db,\
0x0000,\
"reg_buck_05_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_vbit_normal[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1dc,\
0x0000,\
" ",\
" ",\
"reg_buck_05_sw_en_dly_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_sw_en_dly_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x1dd,\
0x0000,\
"reg_buck_05_bg_en_dr",\
"reg_buck_05_bg_en",\
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
{0x1de,\
0x0000,\
"reg_buck_05_sw_en_dr",\
"reg_buck_05_sw_en",\
"reg_buck_05_bg_hi2sw_hi_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_bg_hi2sw_hi_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x1df,\
0x0000,\
" ",\
" ",\
"dig_buck_05_bg_en",\
"dig_buck_05_sw_en",\
" ",\
"reg_buck_05_bg_low2sw_low_fast_cnt[10:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_bg_low2sw_low_slow_cnt[3:2]",\
" ",\
" ",\
" ",\
},\
{0x1e0,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_en_zcd_cal",\
"reg_buck_03_anti_res_disable",\
"reg_buck_03_zcd_cap_bit[7:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1e2,\
0x0000,\
"reg_buck_03_force_reg_bypass",\
" ",\
"reg_buck_03_vcomp_ix2_hp[13:12]",\
" ",\
"reg_buck_03_test_bit[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_03_clk_32k_en",\
"reg_buck_03_nlimit_bit[6:4]",\
" ",\
" ",\
"reg_buck_03_plimit_bit[3:1]",\
" ",\
" ",\
" ",\
},\
{0x1e3,\
0x0000,\
"reg_buck_03_reset_zcd",\
"reg_buck_03_en_ulp_protect_time",\
"reg_buck_03_vcomp_ix2",\
" ",\
"reg_buck_03_counter_sel_mode",\
"reg_buck_03_err_ix2",\
"reg_buck_03_force_vcomp_normal",\
" ",\
" ",\
"reg_buck_03_vcomp_lp[6:4]",\
" ",\
" ",\
"reg_buck_03_pd_clamph",\
"reg_buck_03_pd_clampl",\
"reg_buck_03_protect_time_50u",\
"reg_buck_03_ulp_pulse_en",\
},\
{0x1e4,\
0x0000,\
"reg_buck_03_reserved[15:0]",\
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
{0x1e5,\
0x0000,\
"reg_buck_03_pull_down",\
"reg_buck_03_soft_start_dr",\
"reg_buck_03_soft_start",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_ramp_step[8:4]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_ramp_en  ",\
"reg_buck_03_dsleep_msk",\
"reg_pu_buck_03_dr     ",\
"reg_pu_buck_03        ",\
},\
{0x1e6,\
0x0000,\
"reg_buck_03_force_mode_normal",\
"reg_buck_03_ulp_mode_sel_normal",\
"reg_buck_03_vcomp_vsel_normal",\
"reg_buck_03_reg_mode_normal",\
"reg_buck_03_vcomp_1u_normal",\
"reg_buck_03_ulp_res_normal",\
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
{0x1e7,\
0x0000,\
"reg_buck_03_force_mode_dsleep",\
"reg_buck_03_ulp_mode_sel_dsleep",\
"reg_buck_03_vcomp_vsel_dsleep",\
"reg_buck_03_reg_mode_dsleep",\
"reg_buck_03_vcomp_1u_dsleep",\
"reg_buck_03_ulp_res_dsleep",\
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
{0x1e8,\
0x0000,\
"reg_buck_03_force_mode_rc",\
"reg_buck_03_ulp_mode_sel_rc",\
"reg_buck_03_vcomp_vsel_rc",\
"reg_buck_03_reg_mode_rc",\
"reg_buck_03_vcomp_1u_rc",\
"reg_buck_03_ulp_res_rc",\
"reg_buck_03_force_ulp_res",\
" ",\
"reg_buck_03_vbit_dsleep[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1e9,\
0x0000,\
"reg_buck_03_ton_bit_normal[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_03_ton_bit_dsleep[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_03_ton_bit_rc[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_03_soft_start_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x1ea,\
0x0000,\
" ",\
"reg_buck_03_force_vcomp_10u_normal",\
"reg_buck_03_force_vcomp_10u_dsleep",\
"reg_buck_03_force_vcomp_10u_rc",\
"reg_buck_03_vref_sel_dsleep[11:10]",\
" ",\
"reg_buck_03_vref_sel_rc[9:8]",\
" ",\
"reg_buck_03_vref_sel_normal[7:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1eb,\
0x0000,\
"reg_buck_03_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_vbit_normal[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x1ec,\
0x0000,\
" ",\
" ",\
"reg_buck_03_sw_en_dly_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_sw_en_dly_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x1ed,\
0x0000,\
"reg_buck_03_bg_en_dr",\
"reg_buck_03_bg_en",\
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
{0x1ee,\
0x0000,\
"reg_buck_03_sw_en_dr",\
"reg_buck_03_sw_en",\
"reg_buck_03_bg_hi2sw_hi_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_bg_hi2sw_hi_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x1ef,\
0x0000,\
" ",\
" ",\
"dig_buck_03_bg_en",\
"dig_buck_03_sw_en",\
" ",\
"reg_buck_03_bg_low2sw_low_fast_cnt[10:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_bg_low2sw_low_slow_cnt[3:2]",\
" ",\
" ",\
" ",\
},\
{0x1fe,\
0x0000,\
"dft_result_case0[15:0]",\
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
{0x1ff,\
0x0000,\
"dft_result_case1[15:0]",\
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
{0x202,\
0x0000,\
" ",\
"reg_lp_en_ldo_14_dsleep",\
"reg_lp_en_ldo_14_dr",\
"reg_lp_en_ldo_14",\
"reg_pu_ldo_14_dsleep",\
"reg_pu_ldo_14_dr",\
"reg_pu_ldo_14",\
"reg_ldo_14_pulldown",\
" ",\
" ",\
" ",\
"reg_ldo_14_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_14_ramp_en",\
},\
{0x203,\
0x0000,\
" ",\
"reg_ldo_14_vbit_rc[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_14_vbit_dsleep[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_14_vbit_normal[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x206,\
0x0000,\
"reg_buck_04_abort_source_clr",\
"reg_buck_04_handle_sel_pmu_off",\
"reg_buck_04_hw_mode",\
"reg_buck_04_intr_clr",\
"reg_buck_04_intr_en",\
"reg_buck_04_intr_msk",\
"reg_buck_04_dcdc_off_dr",\
"reg_buck_04_dcdc_off_reg",\
"reg_buck_04_pmu_off_dr",\
"reg_buck_04_pmu_off_reg",\
"reg_buck_04_reboot_cycle[5:2]",\
" ",\
" ",\
" ",\
"reg_buck_04_break_time[1:0]",\
" ",\
},\
{0x207,\
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
"reg_buck_04_protec_cycle[3:2]",\
" ",\
"reg_buck_04_reboot_trigger",\
"reg_buck_04_reboot_trigger_dr",\
},\
{0x20a,\
0x0000,\
" ",\
"reg_lp_en_ldo_15_dsleep",\
"reg_lp_en_ldo_15_dr",\
"reg_lp_en_ldo_15",\
"reg_pu_ldo_15_dsleep",\
"reg_pu_ldo_15_dr",\
"reg_pu_ldo_15",\
"reg_ldo_15_pulldown",\
" ",\
" ",\
" ",\
"reg_ldo_15_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_15_ramp_en",\
},\
{0x20b,\
0x0000,\
" ",\
"reg_ldo_15_vbit_normal[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_15_vbit_dsleep[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_15_vbit_rc[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x210,\
0x0000,\
"reg_ldo_12_bypass",\
"reg_lp_en_ldo_12_dsleep",\
"reg_lp_en_ldo_12_dr",\
"reg_lp_en_ldo_12",\
"reg_pu_ldo_12_dsleep",\
"reg_pu_ldo_12_dr",\
"reg_pu_ldo_12",\
"reg_ldo_12_pulldown",\
" ",\
" ",\
" ",\
"reg_ldo_12_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_12_ramp_en",\
},\
{0x211,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_12_vbit_normal[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_12_vbit_rc[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x212,\
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
"reg_ldo_12_vbit_dsleep[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x216,\
0x0000,\
" ",\
"reg_ldo_11_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_11_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_11_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x217,\
0x0000,\
" ",\
"reg_ldo_11_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_11_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_11_oscp_func_en",\
"reg_ldo_11_ocp_en_dr",\
"reg_ldo_11_ocp_en_reg",\
},\
{0x218,\
0x0000,\
"reg_ldo_11_break_time[15:14]",\
" ",\
"reg_ldo_11_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_11_reboot_trigger",\
"reg_ldo_11_reboot_trigger_dr",\
"reg_ldo_11_ldo_off_dr",\
"reg_ldo_11_ldo_off_reg",\
"reg_ldo_11_pmu_off_dr",\
"reg_ldo_11_pmu_off_reg",\
"reg_ldo_11_protec_cycle[3:2]",\
" ",\
"reg_ldo_11_handle_sel_pmu_off",\
"reg_ldo_11_hw_mode",\
},\
{0x219,\
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
"reg_ldo_11_abort_source_clr",\
"reg_ldo_11_intr_en",\
"reg_ldo_11_intr_msk",\
"reg_ldo_11_intr_clr",\
},\
{0x21a,\
0x0000,\
" ",\
"reg_ldo_12_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_12_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_12_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x21b,\
0x0000,\
" ",\
"reg_ldo_12_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_12_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_12_oscp_func_en",\
"reg_ldo_12_ocp_en_dr",\
"reg_ldo_12_ocp_en_reg",\
},\
{0x21c,\
0x0000,\
"reg_ldo_12_break_time[15:14]",\
" ",\
"reg_ldo_12_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_12_reboot_trigger",\
"reg_ldo_12_reboot_trigger_dr",\
"reg_ldo_12_ldo_off_dr",\
"reg_ldo_12_ldo_off_reg",\
"reg_ldo_12_pmu_off_dr",\
"reg_ldo_12_pmu_off_reg",\
"reg_ldo_12_protec_cycle[3:2]",\
" ",\
"reg_ldo_12_handle_sel_pmu_off",\
"reg_ldo_12_hw_mode",\
},\
{0x21d,\
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
"reg_ldo_12_abort_source_clr",\
"reg_ldo_12_intr_en",\
"reg_ldo_12_intr_msk",\
"reg_ldo_12_intr_clr",\
},\
{0x220,\
0x0000,\
" ",\
" ",\
"reg_buck_03_vcomp_lp_sel",\
" ",\
"reg_buck_03_threshold_sel",\
"reg_buck_03_subharmonic_sel",\
" ",\
"reg_buck_03_cal_deltav[8:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_logic_sel",\
},\
{0x221,\
0x0000,\
" ",\
" ",\
"reg_buck_06_vcomp_lp_sel",\
"reg_buck_06_ulp_pulse_en",\
"reg_buck_06_threshold_sel",\
"reg_buck_06_subharmonic_sel",\
" ",\
"reg_buck_06_cal_deltav[8:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_logic_sel",\
},\
{0x222,\
0x0000,\
"reg_buck_06_err_ix2",\
" ",\
"reg_buck_06_en_zcd_cal",\
"reg_buck_06_en_ulp_protect_time",\
" ",\
"reg_buck_06_counter_sel_mode",\
"reg_buck_06_clk_32k_en",\
"reg_buck_06_pd_clamph",\
"reg_buck_06_pd_clampl",\
"reg_buck_06_plimit_bit[6:4]",\
" ",\
" ",\
"reg_buck_06_nlimit_bit[3:1]",\
" ",\
" ",\
"reg_buck_06_anti_res_disable",\
},\
{0x223,\
0x0000,\
"reg_buck_06_protect_time_50u",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_vcomp_lp[10:8]",\
" ",\
" ",\
"reg_buck_06_pull_down",\
" ",\
"reg_buck_06_zcd_cap_bit[5:2]",\
" ",\
" ",\
" ",\
"reg_buck_06_force_vcomp_normal",\
"reg_buck_06_force_reg_bypass",\
},\
{0x224,\
0x0000,\
"reg_buck_06_reserved[15:0]",\
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
{0x225,\
0x0000,\
" ",\
" ",\
" ",\
"reg_buck_06_force_ulp_res",\
"reg_buck_06_force_vcomp_10u_normal",\
"reg_buck_06_force_vcomp_10u_dsleep",\
"reg_buck_06_force_vcomp_10u_rc",\
"reg_buck_06_vcomp_ix2",\
" ",\
"reg_buck_06_reset_zcd",\
"reg_buck_06_vcomp_ix2_hp[5:4]",\
" ",\
"reg_buck_06_test_bit[3:0]",\
" ",\
" ",\
" ",\
},\
{0x226,\
0x0000,\
" ",\
" ",\
"reg_buck_01_vcomp_lp_sel",\
"reg_buck_01_ulp_pulse_en",\
"reg_buck_01_threshold_sel",\
"reg_buck_01_subharmonic_sel",\
" ",\
"reg_buck_01_cal_deltav[8:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_logic_sel",\
},\
{0x227,\
0x0000,\
"reg_buck_01_err_ix2",\
" ",\
"reg_buck_01_en_zcd_cal",\
"reg_buck_01_en_ulp_protect_time",\
" ",\
"reg_buck_01_counter_sel_mode",\
"reg_buck_01_clk_32k_en",\
"reg_buck_01_pd_clamph",\
"reg_buck_01_pd_clampl",\
"reg_buck_01_plimit_bit[6:4]",\
" ",\
" ",\
"reg_buck_01_nlimit_bit[3:1]",\
" ",\
" ",\
"reg_buck_01_anti_res_disable",\
},\
{0x228,\
0x0000,\
"reg_buck_01_protect_time_50u",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_vcomp_lp[10:8]",\
" ",\
" ",\
"reg_buck_01_pull_down",\
" ",\
"reg_buck_01_zcd_cap_bit[5:2]",\
" ",\
" ",\
" ",\
"reg_buck_01_force_vcomp_normal",\
"reg_buck_01_force_reg_bypass",\
},\
{0x229,\
0x0000,\
"reg_buck_01_reserved[15:0]",\
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
{0x22a,\
0x0000,\
" ",\
" ",\
" ",\
"reg_buck_01_force_ulp_res",\
"reg_buck_01_force_vcomp_10u_normal",\
"reg_buck_01_force_vcomp_10u_dsleep",\
"reg_buck_01_force_vcomp_10u_rc",\
"reg_buck_01_vcomp_ix2",\
" ",\
"reg_buck_01_reset_zcd",\
"reg_buck_01_vcomp_ix2_hp[5:4]",\
" ",\
"reg_buck_01_test_bit[3:0]",\
" ",\
" ",\
" ",\
},\
{0x22b,\
0x0000,\
" ",\
"reg_ldo_13_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_13_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_13_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x22c,\
0x0000,\
" ",\
"reg_ldo_13_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_13_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_13_oscp_func_en",\
"reg_ldo_13_ocp_en_dr",\
"reg_ldo_13_ocp_en_reg",\
},\
{0x22d,\
0x0000,\
"reg_ldo_13_break_time[15:14]",\
" ",\
"reg_ldo_13_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_13_reboot_trigger",\
"reg_ldo_13_reboot_trigger_dr",\
"reg_ldo_13_ldo_off_dr",\
"reg_ldo_13_ldo_off_reg",\
"reg_ldo_13_pmu_off_dr",\
"reg_ldo_13_pmu_off_reg",\
"reg_ldo_13_protec_cycle[3:2]",\
" ",\
"reg_ldo_13_handle_sel_pmu_off",\
"reg_ldo_13_hw_mode",\
},\
{0x22e,\
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
"reg_ldo_13_abort_source_clr",\
"reg_ldo_13_intr_en",\
"reg_ldo_13_intr_msk",\
"reg_ldo_13_intr_clr",\
},\
{0x230,\
0x0000,\
"auto_addr0_data[15:0]",\
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
{0x231,\
0x0000,\
"auto_addr1_data[15:0]",\
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
{0x232,\
0x0000,\
"auto_addr2_data[15:0]",\
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
{0x233,\
0x0000,\
"auto_addr3_data[15:0]",\
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
{0x234,\
0x0000,\
"auto_addr4_data[15:0]",\
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
{0x235,\
0x0000,\
"auto_addr5_data[15:0]",\
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
{0x236,\
0x0000,\
"auto_addr6_data[15:0]",\
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
{0x237,\
0x0000,\
"auto_addr7_data[15:0]",\
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
{0x238,\
0x0000,\
"auto_addr8_data[15:0]",\
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
{0x239,\
0x0000,\
"auto_addr9_data[15:0]",\
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
{0x23a,\
0x0000,\
"auto_addra_data[15:0]",\
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
{0x23b,\
0x0000,\
"auto_addrb_data[15:0]",\
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
{0x23c,\
0x0000,\
"auto_addrc_data[15:0]",\
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
{0x23d,\
0x0000,\
"auto_addrd_data[15:0]",\
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
{0x23e,\
0x0000,\
"auto_addre_data[15:0]",\
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
{0x23f,\
0x0000,\
"auto_addrf_data[15:0]",\
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
{0x240,\
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
"buck_06_oc",\
"buck_05_oc",\
"buck_04_oc",\
"buck_03_oc",\
"buck_02_oc",\
"buck_01_oc",\
},\
{0x241,\
0x0000,\
"pwm_mem_psw_en_dr",\
"pwm_mem_psw_en_reg",\
"pwm_iso_en_dr",\
"pwm_iso_en_reg",\
"pwm_reset_assert_dr",\
"pwm_reset_assert_reg",\
"pwm_psw_en_dr",\
"pwm_psw_en_reg",\
"sdio_mem_psw_en_dr",\
"sdio_mem_psw_en_reg",\
"sdio_iso_en_dr",\
"sdio_iso_en_reg",\
"sdio_reset_assert_dr",\
"sdio_reset_assert_reg",\
"sdio_psw_en_dr",\
"sdio_psw_en_reg",\
},\
{0x243,\
0x0000,\
"reg_buck_05_break_time[15:14]",\
" ",\
"reg_buck_05_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_buck_05_reboot_trigger",\
"reg_buck_05_reboot_trigger_dr",\
"reg_buck_05_dcdc_off_dr",\
"reg_buck_05_dcdc_off_reg",\
"reg_buck_05_pmu_off_dr",\
"reg_buck_05_pmu_off_reg",\
"reg_buck_05_protec_cycle[3:2]",\
" ",\
"reg_buck_05_handle_sel_pmu_off",\
"reg_buck_05_hw_mode",\
},\
{0x244,\
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
"reg_buck_05_abort_source_clr",\
"reg_buck_05_intr_en",\
"reg_buck_05_intr_msk",\
"reg_buck_05_intr_clr",\
},\
{0x247,\
0x0000,\
"reg_ldo_10_bypass",\
"reg_lp_en_ldo_10_dsleep",\
"reg_lp_en_ldo_10_dr",\
"reg_lp_en_ldo_10",\
"reg_pu_ldo_10_dsleep",\
"reg_pu_ldo_10_dr",\
"reg_pu_ldo_10",\
"reg_ldo_10_pulldown",\
" ",\
" ",\
" ",\
"reg_ldo_10_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_10_ramp_en",\
},\
{0x248,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_10_vbit_dsleep[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x249,\
0x0000,\
"reg_ldo_10_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_10_vbit_normal[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x24e,\
0x0000,\
" ",\
"reg_lp_en_ldo_07_dsleep",\
"reg_lp_en_ldo_07_dr",\
"reg_lp_en_ldo_07",\
"reg_pu_ldo_07_dsleep",\
"reg_pu_ldo_07_dr",\
"reg_pu_ldo_07",\
"reg_ldo_07_pulldown",\
" ",\
" ",\
" ",\
"reg_ldo_07_ramp_step[4:1]",\
" ",\
" ",\
" ",\
"reg_ldo_07_ramp_en",\
},\
{0x24f,\
0x0000,\
"reg_ldo_07_vbit_normal[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_07_vbit_rc[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x250,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_07_vbit_dsleep[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x252,\
0x0000,\
" ",\
"reg_buck_03_sleep_ramp_step[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_sleep_ramp_step[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_sleep_ramp_step[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x253,\
0x0000,\
" ",\
"reg_buck_04_sleep_ramp_step[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_sleep_ramp_step[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_sleep_ramp_step[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x254,\
0x0000,\
" ",\
"reg_buck_06_fast_ramp_step[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_fast_ramp_step[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_fast_ramp_step[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x255,\
0x0000,\
" ",\
"reg_buck_03_fast_ramp_step[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_fast_ramp_step[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_fast_ramp_step[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x256,\
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
"reg_buck_refresh_fsm_dbg_mask",\
},\
{0x269,\
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
"reg_buck_02_edge_pconp_rc[5:3]",\
" ",\
" ",\
"reg_buck_02_edge_pconp_dsleep[2:0]",\
" ",\
" ",\
},\
{0x26a,\
0x0000,\
" ",\
"reg_buck_02_edge_pconp_normal[14:12]",\
" ",\
" ",\
"reg_buck_02_edge_pconn_rc[11:9]",\
" ",\
" ",\
"reg_buck_02_edge_pconn_dsleep[8:6]",\
" ",\
" ",\
"reg_buck_02_edge_pconn_normal[5:3]",\
" ",\
" ",\
"reg_buck_02_edge_nconp_rc[2:0]",\
" ",\
" ",\
},\
{0x26b,\
0x0000,\
" ",\
"reg_buck_02_edge_nconp_dsleep[14:12]",\
" ",\
" ",\
"reg_buck_02_edge_nconp_normal[11:9]",\
" ",\
" ",\
"reg_buck_02_edge_nconn_rc[8:6]",\
" ",\
" ",\
"reg_buck_02_edge_nconn_dsleep[5:3]",\
" ",\
" ",\
"reg_buck_02_edge_nconn_normal[2:0]",\
" ",\
" ",\
},\
{0x26c,\
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
"reg_buck_03_edge_pconp_rc[5:3]",\
" ",\
" ",\
"reg_buck_03_edge_pconp_dsleep[2:0]",\
" ",\
" ",\
},\
{0x26d,\
0x0000,\
" ",\
"reg_buck_03_edge_pconp_normal[14:12]",\
" ",\
" ",\
"reg_buck_03_edge_pconn_rc[11:9]",\
" ",\
" ",\
"reg_buck_03_edge_pconn_dsleep[8:6]",\
" ",\
" ",\
"reg_buck_03_edge_pconn_normal[5:3]",\
" ",\
" ",\
"reg_buck_03_edge_nconp_rc[2:0]",\
" ",\
" ",\
},\
{0x26e,\
0x0000,\
" ",\
"reg_buck_03_edge_nconp_dsleep[14:12]",\
" ",\
" ",\
"reg_buck_03_edge_nconp_normal[11:9]",\
" ",\
" ",\
"reg_buck_03_edge_nconn_rc[8:6]",\
" ",\
" ",\
"reg_buck_03_edge_nconn_dsleep[5:3]",\
" ",\
" ",\
"reg_buck_03_edge_nconn_normal[2:0]",\
" ",\
" ",\
},\
{0x26f,\
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
"reg_buck_05_edge_pconp_rc[5:3]",\
" ",\
" ",\
"reg_buck_05_edge_pconp_dsleep[2:0]",\
" ",\
" ",\
},\
{0x270,\
0x0000,\
" ",\
"reg_buck_05_edge_pconp_normal[14:12]",\
" ",\
" ",\
"reg_buck_05_edge_pconn_rc[11:9]",\
" ",\
" ",\
"reg_buck_05_edge_pconn_dsleep[8:6]",\
" ",\
" ",\
"reg_buck_05_edge_pconn_normal[5:3]",\
" ",\
" ",\
"reg_buck_05_edge_nconp_rc[2:0]",\
" ",\
" ",\
},\
{0x271,\
0x0000,\
" ",\
"reg_buck_05_edge_nconp_dsleep[14:12]",\
" ",\
" ",\
"reg_buck_05_edge_nconp_normal[11:9]",\
" ",\
" ",\
"reg_buck_05_edge_nconn_rc[8:6]",\
" ",\
" ",\
"reg_buck_05_edge_nconn_dsleep[5:3]",\
" ",\
" ",\
"reg_buck_05_edge_nconn_normal[2:0]",\
" ",\
" ",\
},\
{0x272,\
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
"reg_buck_06_edge_pconp_rc[5:3]",\
" ",\
" ",\
"reg_buck_06_edge_pconp_dsleep[2:0]",\
" ",\
" ",\
},\
{0x273,\
0x0000,\
" ",\
"reg_buck_06_edge_pconp_normal[14:12]",\
" ",\
" ",\
"reg_buck_06_edge_pconn_rc[11:9]",\
" ",\
" ",\
"reg_buck_06_edge_pconn_dsleep[8:6]",\
" ",\
" ",\
"reg_buck_06_edge_pconn_normal[5:3]",\
" ",\
" ",\
"reg_buck_06_edge_nconp_rc[2:0]",\
" ",\
" ",\
},\
{0x274,\
0x0000,\
" ",\
"reg_buck_06_edge_nconp_dsleep[14:12]",\
" ",\
" ",\
"reg_buck_06_edge_nconp_normal[11:9]",\
" ",\
" ",\
"reg_buck_06_edge_nconn_rc[8:6]",\
" ",\
" ",\
"reg_buck_06_edge_nconn_dsleep[5:3]",\
" ",\
" ",\
"reg_buck_06_edge_nconn_normal[2:0]",\
" ",\
" ",\
},\
{0x27d,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"pmic_vote_valid_1",\
"pmic_vote_bit_1[6:4]",\
" ",\
" ",\
"pmic_vote_valid_0",\
"pmic_vote_bit_0[2:0]",\
" ",\
" ",\
},\
{0x27e,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_active_vote0[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_active_vote1[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x27f,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_active_vote2[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_active_vote3[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x280,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_active_vote4[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_active_vote5[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x281,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_active_vote6[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_01_vbit_active_vote7[5:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x282,\
0x0000,\
"reg_buck_01_vbit_active_vote1[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_vbit_active_vote0[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x283,\
0x0000,\
"reg_buck_01_vbit_active_vote3[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_vbit_active_vote2[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x284,\
0x0000,\
"reg_buck_01_vbit_active_vote5[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_vbit_active_vote4[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x285,\
0x0000,\
"reg_buck_01_vbit_active_vote7[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_vbit_active_vote6[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x288,\
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
"reg_buck_06_zcd_offset_calib_en_dr",\
"reg_buck_05_zcd_offset_calib_en_dr",\
"reg_buck_04_zcd_offset_calib_en_dr",\
"reg_buck_03_zcd_offset_calib_en_dr",\
"reg_buck_02_zcd_offset_calib_en_dr",\
"reg_buck_01_zcd_offset_calib_en_dr",\
},\
{0x290,\
0x0000,\
"reg_buck_06_vbit_active_vote1[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_vbit_active_vote0[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x291,\
0x0000,\
"reg_buck_06_vbit_active_vote3[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_vbit_active_vote2[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x292,\
0x0000,\
"reg_buck_06_vbit_active_vote5[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_vbit_active_vote4[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x293,\
0x0000,\
"reg_buck_06_vbit_active_vote7[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_vbit_active_vote6[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x298,\
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
"o_dft_out[1:0]",\
" ",\
},\
{0x2a0,\
0x0000,\
"reg_buck_04_vbit_active_vote1[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_vbit_active_vote0[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2a1,\
0x0000,\
"reg_buck_04_vbit_active_vote3[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_vbit_active_vote2[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2a2,\
0x0000,\
"reg_buck_04_vbit_active_vote5[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_vbit_active_vote4[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2a3,\
0x0000,\
"reg_buck_04_vbit_active_vote7[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_vbit_active_vote6[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2a8,\
0x0000,\
"reg_buck_05_vbit_active_vote1[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_vbit_active_vote0[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2a9,\
0x0000,\
"reg_buck_05_vbit_active_vote3[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_vbit_active_vote2[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2aa,\
0x0000,\
"reg_buck_05_vbit_active_vote5[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_vbit_active_vote4[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2ab,\
0x0000,\
"reg_buck_05_vbit_active_vote7[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_vbit_active_vote6[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2b0,\
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
"vote_sel_1",\
"vote_sel_0",\
},\
{0x2b1,\
0x0000,\
" ",\
"reg_buck_01_active_ramp_delay_slow[14:11]",\
" ",\
" ",\
" ",\
"reg_buck_01_active_ramp_delay_fast[10:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_active_ramp_delay_en",\
},\
{0x2b2,\
0x0000,\
" ",\
" ",\
" ",\
"reg_pmu2chrg_ldo_on",\
"reg_pmu2chrg_ldo_on_dr",\
"reg_cc_poweron",\
"reg_cc_poweron_dr",\
"reg_clk_cc_div[8:4]",\
" ",\
" ",\
" ",\
" ",\
"reg_clk_cc_sel",\
"reg_clk_cc_rc_en",\
"reg_clk_cc_osc_en",\
"dft_mode_cc",\
},\
{0x2b3,\
0x0000,\
" ",\
" ",\
"reg_ldo_15_pulldown_dr",\
"reg_ldo_14_pulldown_dr",\
"reg_ldo_13_pulldown_dr",\
"reg_ldo_12_pulldown_dr",\
"reg_ldo_11_pulldown_dr",\
"reg_ldo_10_pulldown_dr",\
"reg_ldo_09_pulldown_dr",\
"reg_ldo_08_pulldown_dr",\
"reg_ldo_07_pulldown_dr",\
"reg_ldo_06_pulldown_dr",\
"reg_ldo_05_pulldown_dr",\
"reg_ldo_03_pulldown_dr",\
"reg_ldo_02_pulldown_dr",\
"reg_ldo_01_pulldown_dr",\
},\
{0x2b4,\
0x0000,\
" ",\
"reg_buck_02_active_ramp_delay_slow[14:11]",\
" ",\
" ",\
" ",\
"reg_buck_02_active_ramp_delay_fast[10:1]",\
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
{0x2b5,\
0x0000,\
" ",\
"reg_buck_03_active_ramp_delay_slow[14:11]",\
" ",\
" ",\
" ",\
"reg_buck_03_active_ramp_delay_fast[10:1]",\
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
{0x2b6,\
0x0000,\
" ",\
"reg_buck_04_active_ramp_delay_slow[14:11]",\
" ",\
" ",\
" ",\
"reg_buck_04_active_ramp_delay_fast[10:1]",\
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
{0x2b7,\
0x0000,\
" ",\
"reg_buck_05_active_ramp_delay_slow[14:11]",\
" ",\
" ",\
" ",\
"reg_buck_05_active_ramp_delay_fast[10:1]",\
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
{0x2b8,\
0x0000,\
" ",\
"reg_buck_06_active_ramp_delay_slow[14:11]",\
" ",\
" ",\
" ",\
"reg_buck_06_active_ramp_delay_fast[10:1]",\
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
{0x2c2,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel11[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel10[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2c3,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel13[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel12[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2c4,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel15[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel14[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2c5,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel17[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel16[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2c6,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel19[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel18[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2c7,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel1b[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel1a[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2c8,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel1d[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel1c[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2c9,\
0x0000,\
" ",\
" ",\
"reg_vref_uv_sel1f[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_uv_sel1e[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2ca,\
0x0000,\
" ",\
" ",\
"reg_vref_ov_selb[13:7]",\
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
{0x2cb,\
0x0000,\
" ",\
" ",\
"reg_vref_ov_seld[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_ov_selc[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2cc,\
0x0000,\
" ",\
" ",\
"reg_vref_ov_self[13:7]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vref_ov_sele[6:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2cd,\
0x0000,\
"reg_uv_msk[31:16][15:0]",\
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
{0x2ce,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vcore_l_sw1_break_time[10:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vcore_l_sw1_intr_msk",\
"reg_vcore_l_sw1_intr_en",\
"reg_vcore_l_sw1_abort_source_clr",\
"reg_vcore_l_sw1_intr_clr",\
"reg_vcore_l_sw1_handle_sel_pmu_off",\
},\
{0x2cf,\
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
"vcore_l_sw1_abort_source[4:1]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2d0,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vana_sw2_break_time[10:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vana_sw2_intr_msk",\
"reg_vana_sw2_intr_en",\
"reg_vana_sw2_abort_source_clr",\
"reg_vana_sw2_intr_clr",\
"reg_vana_sw2_handle_sel_pmu_off",\
},\
{0x2d1,\
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
"vana_sw2_abort_source[4:1]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2d2,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vmem_sw3_break_time[10:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vmem_sw3_intr_msk",\
"reg_vmem_sw3_intr_en",\
"reg_vmem_sw3_abort_source_clr",\
"reg_vmem_sw3_intr_clr",\
"reg_vmem_sw3_handle_sel_pmu_off",\
},\
{0x2d3,\
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
"vmem_sw3_abort_source[4:1]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2d4,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vmem_sw4_break_time[10:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vmem_sw4_intr_msk",\
"reg_vmem_sw4_intr_en",\
"reg_vmem_sw4_abort_source_clr",\
"reg_vmem_sw4_intr_clr",\
"reg_vmem_sw4_handle_sel_pmu_off",\
},\
{0x2d5,\
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
"vmem_sw4_abort_source[4:1]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2d6,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vusb_sw5_break_time[10:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vusb_sw5_intr_msk",\
"reg_vusb_sw5_intr_en",\
"reg_vusb_sw5_abort_source_clr",\
"reg_vusb_sw5_intr_clr",\
"reg_vusb_sw5_handle_sel_pmu_off",\
},\
{0x2d7,\
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
"vusb_sw5_abort_source[4:1]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2d8,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vusb_sw6_break_time[10:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vusb_sw6_intr_msk",\
"reg_vusb_sw6_intr_en",\
"reg_vusb_sw6_abort_source_clr",\
"reg_vusb_sw6_intr_clr",\
"reg_vusb_sw6_handle_sel_pmu_off",\
},\
{0x2d9,\
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
"vusb_sw6_abort_source[4:1]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2da,\
0x0000,\
" ",\
"reg_ldo_14_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_14_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_14_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2db,\
0x0000,\
" ",\
"reg_ldo_14_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_14_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_14_oscp_func_en",\
"reg_ldo_14_ocp_en_dr",\
"reg_ldo_14_ocp_en_reg",\
},\
{0x2dc,\
0x0000,\
"reg_ldo_14_break_time[15:14]",\
" ",\
"reg_ldo_14_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_14_reboot_trigger",\
"reg_ldo_14_reboot_trigger_dr",\
"reg_ldo_14_ldo_off_dr",\
"reg_ldo_14_ldo_off_reg",\
"reg_ldo_14_pmu_off_dr",\
"reg_ldo_14_pmu_off_reg",\
"reg_ldo_14_protec_cycle[3:2]",\
" ",\
"reg_ldo_14_handle_sel_pmu_off",\
"reg_ldo_14_hw_mode",\
},\
{0x2dd,\
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
"reg_ldo_14_abort_source_clr",\
"reg_ldo_14_intr_en",\
"reg_ldo_14_intr_msk",\
"reg_ldo_14_intr_clr",\
},\
{0x2de,\
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
"reg_pwm_mux[2:0]",\
" ",\
" ",\
},\
{0x2df,\
0x0000,\
"reg_buck_05_reserved[15:0]",\
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
{0x2e0,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_vcomp_ix2",\
" ",\
"reg_buck_05_reset_zcd",\
"reg_buck_05_vcomp_ix2_hp[5:4]",\
" ",\
"reg_buck_05_test_bit[3:0]",\
" ",\
" ",\
" ",\
},\
{0x2e1,\
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
"reg_ldo_01_pulldown",\
" ",\
" ",\
" ",\
},\
{0x2e2,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_fast_charge_msk",\
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
{0x2e3,\
0x0000,\
" ",\
"reg_ldo_15_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_15_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_15_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2e4,\
0x0000,\
" ",\
"reg_ldo_15_abort_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_15_low_temp_offset[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_ldo_15_oscp_func_en",\
"reg_ldo_15_ocp_en_dr",\
"reg_ldo_15_ocp_en_reg",\
},\
{0x2e5,\
0x0000,\
"reg_ldo_15_break_time[15:14]",\
" ",\
"reg_ldo_15_reboot_cycle[13:10]",\
" ",\
" ",\
" ",\
"reg_ldo_15_reboot_trigger",\
"reg_ldo_15_reboot_trigger_dr",\
"reg_ldo_15_ldo_off_dr",\
"reg_ldo_15_ldo_off_reg",\
"reg_ldo_15_pmu_off_dr",\
"reg_ldo_15_pmu_off_reg",\
"reg_ldo_15_protec_cycle[3:2]",\
" ",\
"reg_ldo_15_handle_sel_pmu_off",\
"reg_ldo_15_hw_mode",\
},\
{0x2e6,\
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
"reg_ldo_15_abort_source_clr",\
"reg_ldo_15_intr_en",\
"reg_ldo_15_intr_msk",\
"reg_ldo_15_intr_clr",\
},\
{0x2e7,\
0x0000,\
"reg_vbat_abort_source_clr",\
"reg_vbat_handle_sel_pmu_off",\
"reg_vbat_hw_mode",\
"reg_vbat_intr_clr",\
"reg_vbat_intr_en",\
"reg_vbat_intr_msk",\
"reg_vbat_ldo_off_dr",\
"reg_vbat_ldo_off_reg",\
"reg_vbat_pmu_off_dr",\
"reg_vbat_pmu_off_reg",\
"reg_vbat_reboot_cycle[5:2]",\
" ",\
" ",\
" ",\
"reg_vbat_break_time[1:0]",\
" ",\
},\
{0x2e8,\
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
"reg_avdd_2p7_bg_reboot_trigger",\
"reg_avdd_2p7_bg_reboot_trigger_dr",\
"reg_vrtc_reboot_trigger",\
"reg_vrtc_reboot_trigger_dr",\
"reg_vbat_reboot_trigger",\
"reg_vbat_reboot_trigger_dr",\
},\
{0x2e9,\
0x0000,\
"reg_vrtc_abort_source_clr",\
"reg_vrtc_handle_sel_pmu_off",\
"reg_vrtc_hw_mode",\
"reg_vrtc_intr_clr",\
"reg_vrtc_intr_en",\
"reg_vrtc_intr_msk",\
"reg_vrtc_ldo_off_dr",\
"reg_vrtc_ldo_off_reg",\
"reg_vrtc_pmu_off_dr",\
"reg_vrtc_pmu_off_reg",\
"reg_vrtc_reboot_cycle[5:2]",\
" ",\
" ",\
" ",\
"reg_vrtc_break_time[1:0]",\
" ",\
},\
{0x2ea,\
0x0000,\
"reg_avdd_2p7_bg_abort_source_clr",\
"reg_avdd_2p7_bg_handle_sel_pmu_off",\
"reg_avdd_2p7_bg_hw_mode",\
"reg_avdd_2p7_bg_intr_clr",\
"reg_avdd_2p7_bg_intr_en",\
"reg_avdd_2p7_bg_intr_msk",\
"reg_avdd_2p7_bg_ldo_off_dr",\
"reg_avdd_2p7_bg_ldo_off_reg",\
"reg_avdd_2p7_bg_pmu_off_dr",\
"reg_avdd_2p7_bg_pmu_off_reg",\
"reg_avdd_2p7_bg_reboot_cycle[5:2]",\
" ",\
" ",\
" ",\
"reg_avdd_2p7_bg_break_time[1:0]",\
" ",\
},\
{0x2eb,\
0x0000,\
"dbg_ldo_10_ramp_done",\
"dbg_ldo_09_ramp_done",\
"dbg_ldo_08_ramp_done",\
"dbg_ldo_07_ramp_done",\
"dbg_ldo_06_ramp_done",\
"dbg_ldo_05_ramp_done",\
" ",\
"dbg_ldo_03_ramp_done",\
"dbg_ldo_02_ramp_done",\
"dbg_ldo_01_ramp_done",\
"dbg_buck_06_ramp_done",\
"dbg_buck_05_ramp_done",\
"dbg_buck_04_ramp_done",\
"dbg_buck_03_ramp_done",\
"dbg_buck_02_ramp_done",\
"dbg_buck_01_ramp_done",\
},\
{0x2ec,\
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
"dbg_ldo_15_ramp_done",\
"dbg_ldo_14_ramp_done",\
"dbg_ldo_13_ramp_done",\
"dbg_ldo_12_ramp_done",\
"dbg_ldo_11_ramp_done",\
},\
{0x2ed,\
0x0000,\
" ",\
"reg_lp_bias_vbit_load",\
"reg_ldo_15_vbit_load",\
"reg_ldo_14_vbit_load",\
"reg_ldo_13_vbit_load",\
"reg_ldo_12_vbit_load",\
"reg_ldo_11_vbit_load",\
"reg_ldo_10_vbit_load",\
"reg_ldo_09_vbit_load",\
"reg_ldo_08_vbit_load",\
"reg_ldo_07_vbit_load",\
"reg_ldo_06_vbit_load",\
"reg_ldo_05_vbit_load",\
"reg_ldo_03_vbit_load",\
"reg_ldo_02_vbit_load",\
"reg_ldo_01_vbit_load",\
},\
{0x2ef,\
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
"reg_buck_06_vbit_load",\
"reg_buck_05_vbit_load",\
"reg_buck_04_vbit_load",\
"reg_buck_03_vbit_load",\
"reg_buck_02_vbit_load",\
"reg_buck_01_vbit_load",\
},\
{0x2f0,\
0x0000,\
"reg_ldo_10_res_sel_dr",\
"reg_ldo_09_res_sel_dr",\
"reg_ldo_08_res_sel_dr",\
"reg_ldo_07_res_sel_dr",\
"reg_ldo_06_res_sel_dr",\
"reg_ldo_05_res_sel_dr",\
" ",\
"reg_ldo_03_res_sel_dr",\
"reg_ldo_02_res_sel_dr",\
"reg_ldo_01_res_sel_dr",\
"reg_buck_06_res_sel_dr",\
"reg_buck_05_res_sel_dr",\
"reg_buck_04_res_sel_dr",\
"reg_buck_03_res_sel_dr",\
"reg_buck_02_res_sel_dr",\
"reg_buck_01_res_sel_dr",\
},\
{0x2f1,\
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
"reg_ldo_15_res_sel_dr",\
"reg_ldo_14_res_sel_dr",\
"reg_ldo_13_res_sel_dr",\
"reg_ldo_12_res_sel_dr",\
"reg_ldo_11_res_sel_dr",\
},\
{0x2f2,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p4_rpd[7:4]",\
" ",\
" ",\
" ",\
"reg_gpio_p4_rpu[3:0]",\
" ",\
" ",\
" ",\
},\
{0x2f3,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p4_data_out[7:4]",\
" ",\
" ",\
" ",\
"reg_gpio_p4_oenb[3:0]",\
" ",\
" ",\
" ",\
},\
{0x2f4,\
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
"reg_gpio_p4_rx_en[3:0]",\
" ",\
" ",\
" ",\
},\
{0x2f5,\
0x0000,\
"reg_gpio_p5_rpd[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p5_rpu[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2f6,\
0x0000,\
"reg_gpio_p5_data_out[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p5_oenb[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2f7,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p5_rx_en[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2f8,\
0x0000,\
"reg_gpio_p6_rpd[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p6_rpu[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2f9,\
0x0000,\
"reg_gpio_p6_data_out[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p6_oenb[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2fa,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p6_rx_en[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2fb,\
0x0000,\
"reg_gpio_p7_rpd[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p7_rpu[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2fc,\
0x0000,\
"reg_gpio_p7_data_out[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p7_oenb[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2fd,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p7_rx_en[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x2fe,\
0x0000,\
"gpio_p5_data_in[15:8]",\
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
"gpio_p4_data_in[3:0]",\
" ",\
" ",\
" ",\
},\
{0x2ff,\
0x0000,\
"gpio_p7_data_in[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p6_data_in[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x301,\
0x0000,\
"reg_gpio_p4_intr_nedg_clr[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p4_intr_clr[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x302,\
0x0000,\
"gpio_p4_intr_nedg_msk[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p4_intr_msk[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x303,\
0x0000,\
"reg_gpio_p4_lowlvl_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p4_edge_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x304,\
0x0000,\
"reg_gpio_p4_neg_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p4_pos_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x305,\
0x0000,\
"reg_gpio_p4_intr_en[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p4_db_bypass[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x306,\
0x0000,\
"reg_gpio_p5_db_target[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p4_db_target[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x307,\
0x0000,\
"reg_gpio_p5_intr_nedg_clr[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p5_intr_clr[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x308,\
0x0000,\
"gpio_p5_intr_nedg_msk[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p5_intr_msk[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x309,\
0x0000,\
"reg_gpio_p5_lowlvl_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p5_edge_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x30a,\
0x0000,\
"reg_gpio_p5_neg_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p5_pos_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x30b,\
0x0000,\
"reg_gpio_p5_intr_en[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p5_db_bypass[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x30e,\
0x0000,\
"reg_gpio_p6_intr_nedg_clr[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p6_intr_clr[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x30f,\
0x0000,\
"gpio_p6_intr_nedg_msk[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p6_intr_msk[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x310,\
0x0000,\
"reg_gpio_p6_lowlvl_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p6_edge_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x311,\
0x0000,\
"reg_gpio_p6_neg_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p6_pos_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x312,\
0x0000,\
"reg_gpio_p6_intr_en[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p6_db_bypass[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x313,\
0x0000,\
"reg_gpio_p7_db_target[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p6_db_target[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x314,\
0x0000,\
"reg_gpio_p7_intr_nedg_clr[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p7_intr_clr[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x315,\
0x0000,\
"gpio_p7_intr_nedg_msk[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"gpio_p7_intr_msk[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x316,\
0x0000,\
"reg_gpio_p7_lowlvl_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p7_edge_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x317,\
0x0000,\
"reg_gpio_p7_neg_intr_sel[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p7_pos_intr_sel[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x318,\
0x0000,\
"reg_gpio_p7_intr_en[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_gpio_p7_db_bypass[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x31a,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_abort_time[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_oscp_func_en",\
" ",\
" ",\
},\
{0x31c,\
0x0000,\
" ",\
" ",\
"reg_buck_06_sw_en_dly_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_sw_en_dly_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x31d,\
0x0000,\
"reg_buck_06_bg_en_dr",\
"reg_buck_06_bg_en",\
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
{0x31e,\
0x0000,\
"reg_buck_06_sw_en_dr",\
"reg_buck_06_sw_en",\
"reg_buck_06_bg_hi2sw_hi_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_bg_hi2sw_hi_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x31f,\
0x0000,\
" ",\
" ",\
"dig_buck_06_bg_en",\
"dig_buck_06_sw_en",\
" ",\
"reg_buck_06_bg_low2sw_low_fast_cnt[10:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_bg_low2sw_low_slow_cnt[3:2]",\
" ",\
" ",\
" ",\
},\
{0x321,\
0x0000,\
" ",\
" ",\
"reg_buck_01_sw_en_dly_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_sw_en_dly_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x322,\
0x0000,\
"reg_buck_01_bg_en_dr",\
"reg_buck_01_bg_en",\
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
{0x323,\
0x0000,\
"reg_buck_01_sw_en_dr",\
"reg_buck_01_sw_en",\
"reg_buck_01_bg_hi2sw_hi_fast_cnt[13:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_bg_hi2sw_hi_slow_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x324,\
0x0000,\
" ",\
" ",\
"dig_buck_01_bg_en",\
"dig_buck_01_sw_en",\
" ",\
"reg_buck_01_bg_low2sw_low_fast_cnt[10:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_bg_low2sw_low_slow_cnt[3:2]",\
" ",\
" ",\
" ",\
},\
{0x325,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_fast_charge_dr",\
"reg_buck_06_fast_charge",\
"reg_buck_05_fast_charge_dr",\
"reg_buck_05_fast_charge",\
"reg_buck_04_fast_charge_dr",\
"reg_buck_04_fast_charge",\
"reg_buck_03_fast_charge_dr",\
"reg_buck_03_fast_charge",\
"reg_buck_02_fast_charge_dr",\
"reg_buck_02_fast_charge",\
"reg_buck_01_fast_charge_dr",\
"reg_buck_01_fast_charge",\
},\
{0x326,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_abort_time[7:3]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_oscp_func_en",\
" ",\
" ",\
},\
{0x327,\
0x0000,\
" ",\
"reg_buck_03_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x328,\
0x0000,\
" ",\
"reg_buck_05_det_time[14:10]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_det_trubo_time[9:5]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_endure_time[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x32a,\
0x0000,\
"rtc_ms_match_value_0[15:0][15:0]",\
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
{0x32b,\
0x0000,\
"rtc_ms_match_value_0[31:16][15:0]",\
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
{0x32c,\
0x0000,\
"rtc_ms_match_value_1[15:0][15:0]",\
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
{0x32d,\
0x0000,\
"rtc_ms_match_value_1[31:16][15:0]",\
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
{0x32f,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"rtc_ms_int_en_1",\
"rtc_ms_int_en_0",\
"rtc_ms_int1_msk",\
"rtc_ms_int0_msk",\
"rtc_ms_int_1",\
"rtc_ms_int_0",\
"rtc_ms_int_clr_1",\
"rtc_ms_int_clr_0",\
"rtc_ms_int1_msked",\
"rtc_ms_int0_msked",\
"rtc_ms_load",\
},\
{0x330,\
0x0000,\
"rtc_ms_load_value[15:0] [15:0]",\
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
{0x331,\
0x0000,\
"rtc_ms_load_value[31:16][15:0]",\
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
{0x332,\
0x0000,\
"rtc_ms_value[15:0] [15:0]",\
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
{0x333,\
0x0000,\
"rtc_ms_value[31:16][15:0]",\
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
{0x334,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"rtc_ms_valid",\
"rtc_ms_value_ms[9:0]",\
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
{0x335,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"rtc_ms_match_value_ms_0[9:0]",\
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
{0x336,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"rtc_ms_match_value_ms_1[9:0]",\
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
{0x337,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"rtc_ms_load_value_ms[9:0]",\
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
{0x338,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_clk_lpo_idet_en",\
"reg_clk_lpo_udet_en",\
"reg_fast_ramp_slp_sel[7:4]",\
" ",\
" ",\
" ",\
"reg_power_mode_slp_sel[3:0]",\
" ",\
" ",\
" ",\
},\
{0x33b,\
0x0000,\
"abort_intr[31:16][15:0]",\
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
{0x33c,\
0x0000,\
"abort_intr[15:0][15:0]",\
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
{0x33d,\
0x0000,\
"reg_buck_02_zcd_offset_pol_sel",\
"reg_buck_02_zcd_offset_calib_en",\
"reg_buck_02_zcd_offset_dr",\
"reg_buck_02_zcd_offset[12:8]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_zcd_offset_pol_sel",\
"reg_buck_04_zcd_offset_calib_en",\
"reg_buck_04_zcd_offset_dr",\
"reg_buck_04_zcd_offset[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x33e,\
0x0000,\
" ",\
" ",\
"dig_buck_02_zcd_offset[13:9]",\
" ",\
" ",\
" ",\
" ",\
"dig_buck_04_zcd_offset[8:4]",\
" ",\
" ",\
" ",\
" ",\
"dig_buck_02_cal_zcd_offset_mode",\
"dig_buck_04_cal_zcd_offset_mode",\
"buck_02_zcd_out",\
"buck_04_zcd_out",\
},\
{0x33f,\
0x0000,\
" ",\
" ",\
"dig_buck_06_zcd_offset[13:9]",\
" ",\
" ",\
" ",\
" ",\
"dig_buck_01_zcd_offset[8:4]",\
" ",\
" ",\
" ",\
" ",\
"dig_buck_06_cal_zcd_offset_mode",\
"dig_buck_01_cal_zcd_offset_mode",\
"buck_06_zcd_out",\
"buck_01_zcd_out",\
},\
{0x340,\
0x0000,\
" ",\
" ",\
"dig_buck_05_zcd_offset[13:9]",\
" ",\
" ",\
" ",\
" ",\
"dig_buck_03_zcd_offset[8:4]",\
" ",\
" ",\
" ",\
" ",\
"dig_buck_05_cal_zcd_offset_mode",\
"dig_buck_03_cal_zcd_offset_mode",\
"buck_05_zcd_out",\
"buck_03_zcd_out",\
},\
{0x341,\
0x0000,\
"reg_buck_06_zcd_offset_pol_sel",\
"reg_buck_06_zcd_offset_calib_en",\
"reg_buck_06_zcd_offset_dr",\
"reg_buck_06_zcd_offset[12:8]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_zcd_offset_pol_sel",\
"reg_buck_01_zcd_offset_calib_en",\
"reg_buck_01_zcd_offset_dr",\
"reg_buck_01_zcd_offset[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x342,\
0x0000,\
"reg_buck_03_zcd_offset_pol_sel",\
"reg_buck_03_zcd_offset_calib_en",\
"reg_buck_03_zcd_offset_dr",\
"reg_buck_03_zcd_offset[12:8]",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_zcd_offset_pol_sel",\
"reg_buck_05_zcd_offset_calib_en",\
"reg_buck_05_zcd_offset_dr",\
"reg_buck_05_zcd_offset[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x343,\
0x0000,\
"gpio_p0_3_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p0_2_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p0_1_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p0_0_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x344,\
0x0000,\
"gpio_p0_7_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p0_6_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p0_5_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p0_4_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x346,\
0x0000,\
"gpio_p1_3_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p1_2_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p1_1_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p1_0_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x347,\
0x0000,\
"gpio_p1_7_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p1_6_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p1_5_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p1_4_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x348,\
0x0000,\
"gpio_p2_3_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p2_2_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p2_1_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p2_0_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x349,\
0x0000,\
"gpio_p2_7_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p2_6_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p2_5_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p2_4_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x34a,\
0x0000,\
"gpio_p3_3_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p3_2_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p3_1_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p3_0_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x34b,\
0x0000,\
"gpio_p3_7_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p3_6_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p3_5_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p3_4_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x34c,\
0x0000,\
"gpio_p4_3_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p4_2_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p4_1_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p4_0_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x34d,\
0x0000,\
"gpio_p4_7_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p4_6_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p4_5_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p4_4_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x34e,\
0x0000,\
"gpio_p5_3_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p5_2_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p5_1_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p5_0_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x34f,\
0x0000,\
"gpio_p5_7_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p5_6_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p5_5_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p5_4_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x350,\
0x0000,\
"gpio_p6_3_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p6_2_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p6_1_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p6_0_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x351,\
0x0000,\
"gpio_p6_7_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p6_6_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p6_5_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p6_4_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x352,\
0x0000,\
"gpio_p7_3_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p7_2_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p7_1_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p7_0_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x353,\
0x0000,\
"gpio_p7_7_sel_regcfg[15:12]",\
" ",\
" ",\
" ",\
"gpio_p7_6_sel_regcfg[11:8]",\
" ",\
" ",\
" ",\
"gpio_p7_5_sel_regcfg[7:4]",\
" ",\
" ",\
" ",\
"gpio_p7_4_sel_regcfg[3:0]",\
" ",\
" ",\
" ",\
},\
{0x354,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
"buck_06_clk_32k_gate_en",\
"buck_05_clk_32k_gate_en",\
"buck_04_clk_32k_gate_en",\
"buck_03_clk_32k_gate_en",\
"buck_02_clk_32k_gate_en",\
"buck_01_clk_32k_gate_en",\
"ana_test_sel_regcfg[4:1]",\
" ",\
" ",\
" ",\
"clk_rtc_ms_en",\
},\
{0x355,\
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
"dbg_ldo_lp_bias_ramp_done",\
"s_fsm_busy",\
},\
{0x356,\
0x0000,\
" ",\
" ",\
" ",\
"power_up_ord13",\
"power_up_ord12",\
"power_up_ord11",\
"power_up_ord10",\
"power_up_ord9",\
"power_up_ord8",\
"power_up_ord7",\
"power_up_ord6",\
"power_up_ord5",\
"power_up_ord4",\
"power_up_ord3",\
"power_up_ord2",\
"power_up_ord1",\
},\
{0x357,\
0x0000,\
"reg_avdd_2p7_sar_abort_source_clr",\
"reg_avdd_2p7_sar_handle_sel_pmu_off",\
"reg_avdd_2p7_sar_hw_mode",\
"reg_avdd_2p7_sar_intr_clr",\
"reg_avdd_2p7_sar_intr_en",\
"reg_avdd_2p7_sar_intr_msk",\
"reg_avdd_2p7_sar_ldo_off_dr",\
"reg_avdd_2p7_sar_ldo_off_reg",\
"reg_avdd_2p7_sar_pmu_off_dr",\
"reg_avdd_2p7_sar_pmu_off_reg",\
"reg_avdd_2p7_sar_reboot_cycle[5:2]",\
" ",\
" ",\
" ",\
"reg_avdd_2p7_sar_break_time[1:0]",\
" ",\
},\
{0x358,\
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
"reg_avdd_2p7_sar_reboot_trigger",\
"reg_avdd_2p7_sar_reboot_trigger_dr",\
},\
{0x359,\
0x0000,\
"reg_buck_06_force_mode_normal",\
"reg_buck_06_ulp_mode_sel_normal",\
"reg_buck_06_vcomp_vsel_normal",\
"reg_buck_06_reg_mode_normal",\
"reg_buck_06_vcomp_1u_normal",\
"reg_buck_06_ulp_res_normal",\
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
{0x35b,\
0x0000,\
"reg_buck_06_force_mode_dsleep",\
"reg_buck_06_ulp_mode_sel_dsleep",\
"reg_buck_06_vcomp_vsel_dsleep",\
"reg_buck_06_reg_mode_dsleep",\
"reg_buck_06_vcomp_1u_dsleep",\
"reg_buck_06_ulp_res_dsleep",\
" ",\
" ",\
"reg_buck_06_vbit_dsleep[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x35c,\
0x0000,\
"reg_buck_06_vbit_rc[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_vbit_normal[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x35d,\
0x0000,\
"reg_buck_06_force_mode_rc",\
"reg_buck_06_ulp_mode_sel_rc",\
"reg_buck_06_vcomp_vsel_rc",\
"reg_buck_06_reg_mode_rc",\
"reg_buck_06_vcomp_1u_rc",\
"reg_buck_06_ulp_res_rc",\
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
{0x35e,\
0x0000,\
"reg_buck_06_ton_bit_normal[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_06_ton_bit_dsleep[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_06_ton_bit_rc[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_06_soft_start_cnt[3:0]",\
" ",\
" ",\
" ",\
},\
{0x35f,\
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
"reg_buck_06_dsleep_msk",\
"reg_buck_06_soft_start_dr",\
"reg_buck_06_soft_start",\
"reg_pu_buck_06_dr     ",\
"reg_pu_buck_06",\
},\
{0x360,\
0x0000,\
"reg_ldo_07_ilimit_sel[15:14]",\
" ",\
"reg_ldo_06_pull_down_res[13:12]",\
" ",\
"reg_ldo_06_light_load",\
"reg_ldo_06_ilimit_sel[10:9]",\
" ",\
"reg_ldo_05_pull_down_res[8:7]",\
" ",\
"reg_ldo_05_en_leakage_track",\
"reg_ldo_03_pull_down_res[5:4]",\
" ",\
"reg_ldo_03_en_leakage_track",\
"reg_ldo_02_pull_down_res[2:1]",\
" ",\
"reg_ldo_02_en_leakage_track",\
},\
{0x361,\
0x0000,\
"reg_ldo_14_pull_down_res[15:14]",\
" ",\
"reg_ldo_14_en_leakage_track",\
"reg_ldo_13_pull_down_res[12:11]",\
" ",\
"reg_ldo_13_en_leakage_track",\
"reg_ldo_12_pull_down_res[9:8]",\
" ",\
"reg_ldo_12_light_load",\
"reg_ldo_12_ilimit_sel[6:5]",\
" ",\
"reg_ldo_07_pull_down_res[4:3]",\
" ",\
" ",\
" ",\
"reg_ldo_07_light_load",\
},\
{0x362,\
0x0000,\
"reg_rfpa_on_b",\
"reg_rfpa_1p8_res[14:11]",\
" ",\
" ",\
" ",\
"reg_rfpa_1p8",\
"reg_rfpa_1p1_res[9:6]",\
" ",\
" ",\
" ",\
"reg_rfpa_1p1",\
"reg_ldo_15_pull_down_res[4:3]",\
" ",\
" ",\
" ",\
"reg_ldo_15_en_leakage_track",\
},\
{0x363,\
0x0000,\
" ",\
"reg_sar_mode_sel",\
"reg_sar_lp_vrefbuf[13:11]",\
" ",\
" ",\
"reg_sar_lp_sample[10:8]",\
" ",\
" ",\
"reg_sar_lp_dvddreg[7:5]",\
" ",\
" ",\
"reg_sar_bypass_buf",\
"reg_pu_sar_vref_sw",\
" ",\
"reg_rtc_lpo_ibias_sel[1:0]",\
" ",\
},\
{0x364,\
0x0000,\
" ",\
" ",\
"reg_vcm_en",\
"reg_vcm_en_lpf",\
"reg_trim_rcosc[11:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_sar_therm_gain[5:4]",\
" ",\
"reg_sar_pu_ovp",\
"reg_sar_op_ibit[2:0]",\
" ",\
" ",\
},\
{0x365,\
0x0000,\
" ",\
"reg_vref_sel_sensor",\
"reg_vcm_pull_down",\
"reg_vcm_lp_en",\
"reg_vcm_low_vcm_lpf[11:8]",\
" ",\
" ",\
" ",\
"reg_vcm_low_vcm_lp[7:4]",\
" ",\
" ",\
" ",\
"reg_vcm_low_vcm[3:0]",\
" ",\
" ",\
" ",\
},\
{0x366,\
0x0000,\
"reg_buck_01_dt_nr[15:14]",\
" ",\
" ",\
" ",\
"reg_en_bg_aux_buf",\
"reg_bg_notch_en",\
"reg_pmu_vsel2[9:7]",\
" ",\
" ",\
"reg_pmu_vsel1[6:4]",\
" ",\
" ",\
"reg_vrtc_res_sel[3:0]",\
" ",\
" ",\
" ",\
},\
{0x367,\
0x0000,\
"reg_buck_01_force_pon",\
"reg_buck_01_force_plimit_on",\
"reg_buck_01_force_non",\
"reg_buck_01_force_nlimit_on",\
"reg_buck_01_force_clamp_on",\
"reg_buck_01_errout_buf_en",\
"reg_buck_01_erramp_sel_200k",\
"reg_buck_01_err_idiv2",\
"reg_buck_01_en_ss",\
"reg_buck_01_en_detlx_pdrvf",\
"reg_buck_01_en_detlx_ndrvr",\
"reg_buck_01_dvs_sync_en",\
" ",\
" ",\
"reg_buck_01_dt_pr[1:0]",\
" ",\
},\
{0x368,\
0x0000,\
"reg_buck_01_offset_bit[15:11]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_01_nlimit_logic_sel",\
"reg_buck_01_hys_sel",\
"reg_buck_01_gm_option",\
"reg_buck_01_force_vref_reg_bypass_lvbat",\
"reg_buck_01_force_ton_on",\
"reg_buck_01_force_pwm_low",\
" ",\
"reg_buck_01_force_pwm_high",\
},\
{0x369,\
0x0000,\
"reg_buck_01_vref_fast_charge_force_dis",\
"reg_buck_01_vref_buf_en",\
"reg_buck_01_vref_bg_sw_en",\
"reg_buck_01_vcomp_sel_2p4",\
"reg_buck_01_ulp_threshold_sel",\
"reg_buck_01_test_mode",\
"reg_buck_01_ss_fast",\
"reg_buck_01_ramp_x2",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x36a,\
0x0000,\
"reg_buck_02_err_idiv2",\
"reg_buck_02_en_ss",\
"reg_buck_02_en_detlx_pdrvf",\
"reg_buck_02_en_detlx_ndrvr",\
"reg_buck_02_dvs_sync_en",\
"reg_buck_02_dt_pr[10:9]",\
" ",\
"reg_buck_02_dt_nr[8:7]",\
" ",\
"reg_buck_01_en_pblock",\
"reg_buck_01_en_nblock",\
"reg_buck_01_vreg_lp_src",\
"reg_buck_01_vreg_lp_load",\
"reg_buck_01_vreg_lp",\
" ",\
"reg_buck_01_vref_vsel",\
},\
{0x36b,\
0x0000,\
" ",\
"reg_buck_02_nlimit_logic_sel",\
"reg_buck_02_hys_sel",\
"reg_buck_02_gm_option",\
"reg_buck_02_force_vref_reg_bypass_lvbat",\
"reg_buck_02_force_ton_on",\
"reg_buck_02_force_pwm_low",\
"reg_buck_02_force_pwm_high",\
"reg_buck_02_force_pon",\
"reg_buck_02_force_plimit_on",\
"reg_buck_02_force_non",\
"reg_buck_02_force_nlimit_on",\
"reg_buck_02_force_clamp_on",\
"reg_buck_02_errout_buf_en",\
" ",\
"reg_buck_02_erramp_sel_200k",\
},\
{0x36c,\
0x0000,\
"reg_buck_02_vcomp_sel_2p4",\
"reg_buck_02_ulp_threshold_sel",\
"reg_buck_02_test_mode",\
"reg_buck_02_ss_fast",\
"reg_buck_02_ramp_x2",\
" ",\
" ",\
" ",\
"reg_buck_02_offset_bit[7:3]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x36d,\
0x0000,\
"reg_buck_02_en_pblock[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_02_en_nblock[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_02_vreg_lp_src",\
"reg_buck_02_vreg_lp_load",\
"reg_buck_02_vreg_lp",\
"reg_buck_02_vref_vsel",\
"reg_buck_02_vref_fast_charge_force_dis",\
"reg_buck_02_vref_buf_en",\
" ",\
"reg_buck_02_vref_bg_sw_en",\
},\
{0x36e,\
0x0000,\
"reg_buck_03_force_clamp_on",\
"reg_buck_03_errout_buf_en",\
"reg_buck_03_erramp_sel_200k",\
"reg_buck_03_err_idiv2",\
"reg_buck_03_en_ss",\
"reg_buck_03_en_detlx_pdrvf",\
"reg_buck_03_en_detlx_ndrvr",\
"reg_buck_03_dvs_sync_en",\
"reg_buck_03_dt_pr[7:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_dt_nr[1:0]",\
" ",\
},\
{0x36f,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_nlimit_logic_sel",\
"reg_buck_03_hys_sel",\
"reg_buck_03_gm_option",\
"reg_buck_03_force_vref_reg_bypass_lvbat",\
"reg_buck_03_force_ton_on",\
"reg_buck_03_force_pwm_low",\
"reg_buck_03_force_pwm_high",\
"reg_buck_03_force_pon",\
"reg_buck_03_force_plimit_on",\
"reg_buck_03_force_non",\
" ",\
"reg_buck_03_force_nlimit_on",\
},\
{0x370,\
0x0000,\
"reg_buck_03_vref_fast_charge_force_dis",\
"reg_buck_03_vref_buf_en",\
"reg_buck_03_vref_bg_sw_en",\
"reg_buck_03_vcomp_sel_2p4",\
"reg_buck_03_ulp_threshold_sel",\
"reg_buck_03_test_mode",\
"reg_buck_03_ss_fast",\
"reg_buck_03_ramp_x2",\
" ",\
" ",\
" ",\
"reg_buck_03_offset_bit[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x371,\
0x0000,\
" ",\
"reg_buck_04_dt_nr[14:13]",\
" ",\
"reg_buck_03_en_pblock[12:9]",\
" ",\
" ",\
" ",\
"reg_buck_03_en_nblock[8:5]",\
" ",\
" ",\
" ",\
"reg_buck_03_vreg_lp_src",\
"reg_buck_03_vreg_lp_load",\
"reg_buck_03_vreg_lp",\
" ",\
"reg_buck_03_vref_vsel",\
},\
{0x372,\
0x0000,\
"reg_buck_04_force_pwm_low",\
"reg_buck_04_force_pwm_high",\
"reg_buck_04_force_pon",\
"reg_buck_04_force_plimit_on",\
"reg_buck_04_force_non",\
"reg_buck_04_force_nlimit_on",\
"reg_buck_04_force_clamp_on",\
"reg_buck_04_errout_buf_en",\
"reg_buck_04_erramp_sel_200k",\
"reg_buck_04_err_idiv2",\
"reg_buck_04_en_ss",\
"reg_buck_04_en_detlx_pdrvf",\
"reg_buck_04_en_detlx_ndrvr",\
"reg_buck_04_dvs_sync_en",\
"reg_buck_04_dt_pr[1:0]",\
" ",\
},\
{0x373,\
0x0000,\
" ",\
" ",\
"reg_buck_04_offset_bit[13:9]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_nlimit_logic_sel",\
"reg_buck_04_hys_sel",\
"reg_buck_04_gm_option",\
"reg_buck_04_force_vref_reg_bypass_lvbat",\
" ",\
"reg_buck_04_force_ton_on",\
},\
{0x374,\
0x0000,\
" ",\
"reg_buck_04_vreg_lp_src",\
"reg_buck_04_vreg_lp_load",\
"reg_buck_04_vreg_lp",\
"reg_buck_04_vref_vsel",\
"reg_buck_04_vref_fast_charge_force_dis",\
"reg_buck_04_vref_buf_en",\
"reg_buck_04_vref_bg_sw_en",\
"reg_buck_04_vcomp_sel_2p4",\
"reg_buck_04_ulp_threshold_sel",\
"reg_buck_04_test_mode",\
"reg_buck_04_ss_fast",\
"reg_buck_04_ramp_x2",\
" ",\
" ",\
" ",\
},\
{0x375,\
0x0000,\
"reg_buck_04_en_pblock[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_en_nblock[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x376,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_subharmonic_sel",\
"reg_buck_05_threshold_sel",\
"reg_buck_05_ulp_pulse_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_vcomp_lp_sel",\
},\
{0x377,\
0x0000,\
" ",\
" ",\
"reg_buck_05_pd_clampl",\
"reg_buck_05_pd_clamph",\
"reg_buck_05_clk_32k_en",\
"reg_buck_05_counter_sel_mode",\
"reg_buck_05_en_ulp_protect_time",\
"reg_buck_05_en_zcd_cal",\
"reg_buck_05_err_ix2",\
"reg_buck_05_logic_sel",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x378,\
0x0000,\
"reg_buck_05_zcd_cap_bit[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_05_pull_down",\
"reg_buck_05_vcomp_lp[10:8]",\
" ",\
" ",\
"reg_buck_05_protect_time_50u",\
"reg_buck_05_anti_res_disable",\
"reg_buck_05_nlimit_bit[5:3]",\
" ",\
" ",\
"reg_buck_05_plimit_bit[2:0]",\
" ",\
" ",\
},\
{0x379,\
0x0000,\
"reg_buck_05_erramp_sel_200k",\
"reg_buck_05_err_idiv2",\
"reg_buck_05_en_ss",\
"reg_buck_05_en_detlx_pdrvf",\
"reg_buck_05_en_detlx_ndrvr",\
"reg_buck_05_dvs_sync_en",\
"reg_buck_05_dt_pr[9:8]",\
" ",\
"reg_buck_05_dt_nr[7:6]",\
" ",\
"reg_buck_05_force_reg_bypass",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_force_vcomp_normal",\
},\
{0x37a,\
0x0000,\
" ",\
" ",\
"reg_buck_05_nlimit_logic_sel",\
"reg_buck_05_hys_sel",\
"reg_buck_05_gm_option",\
"reg_buck_05_force_vref_reg_bypass_lvbat",\
"reg_buck_05_force_ton_on",\
"reg_buck_05_force_pwm_low",\
"reg_buck_05_force_pwm_high",\
"reg_buck_05_force_pon",\
"reg_buck_05_force_plimit_on",\
"reg_buck_05_force_non",\
"reg_buck_05_force_nlimit_on",\
"reg_buck_05_force_clamp_on",\
" ",\
"reg_buck_05_errout_buf_en",\
},\
{0x37b,\
0x0000,\
"reg_buck_05_vcomp_sel_2p4",\
"reg_buck_05_ulp_threshold_sel",\
"reg_buck_05_test_mode",\
"reg_buck_05_ss_fast",\
"reg_buck_05_ramp_x2",\
" ",\
" ",\
" ",\
"reg_buck_05_offset_bit[7:3]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x37c,\
0x0000,\
"reg_buck_05_en_pblock[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_05_en_nblock[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_05_vreg_lp_src",\
"reg_buck_05_vreg_lp_load",\
"reg_buck_05_vreg_lp",\
"reg_buck_05_vref_vsel",\
"reg_buck_05_vref_fast_charge_force_dis",\
"reg_buck_05_vref_buf_en",\
" ",\
"reg_buck_05_vref_bg_sw_en",\
},\
{0x37d,\
0x0000,\
"reg_buck_06_force_clamp_on",\
"reg_buck_06_errout_buf_en",\
"reg_buck_06_erramp_sel_200k",\
"reg_buck_06_err_idiv2",\
"reg_buck_06_en_ss",\
"reg_buck_06_en_detlx_pdrvf",\
"reg_buck_06_en_detlx_ndrvr",\
"reg_buck_06_dvs_sync_en",\
"reg_buck_06_dt_pr[7:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_dt_nr[1:0]",\
" ",\
},\
{0x37e,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_nlimit_logic_sel",\
"reg_buck_06_hys_sel",\
"reg_buck_06_gm_option",\
"reg_buck_06_force_vref_reg_bypass_lvbat",\
"reg_buck_06_force_ton_on",\
"reg_buck_06_force_pwm_low",\
"reg_buck_06_force_pwm_high",\
"reg_buck_06_force_pon",\
"reg_buck_06_force_plimit_on",\
"reg_buck_06_force_non",\
" ",\
"reg_buck_06_force_nlimit_on",\
},\
{0x37f,\
0x0000,\
"reg_buck_06_vref_fast_charge_force_dis",\
"reg_buck_06_vref_buf_en",\
"reg_buck_06_vref_bg_sw_en",\
"reg_buck_06_vcomp_sel_2p4",\
"reg_buck_06_ulp_threshold_sel",\
"reg_buck_06_test_mode",\
"reg_buck_06_ss_fast",\
"reg_buck_06_ramp_x2",\
" ",\
" ",\
" ",\
"reg_buck_06_offset_bit[4:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x380,\
0x0000,\
" ",\
" ",\
" ",\
"reg_buck_06_vcomp_cal_en",\
"reg_buck_05_vcomp_cal_en",\
"reg_buck_04_vcomp_cal_en",\
"reg_buck_03_vcomp_cal_en",\
"reg_buck_02_vcomp_cal_en",\
"reg_buck_01_vcomp_cal_en",\
"reg_buck_06_en_pblock",\
"reg_buck_06_en_nblock",\
"reg_buck_06_vreg_lp_src",\
"reg_buck_06_vreg_lp_load",\
"reg_buck_06_vreg_lp",\
" ",\
"reg_buck_06_vref_vsel",\
},\
{0x381,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_vref_fast_charge_bit[11:10]",\
" ",\
"reg_buck_05_vref_fast_charge_bit[9:8]",\
" ",\
"reg_buck_04_vref_fast_charge_bit[7:6]",\
" ",\
"reg_buck_03_vref_fast_charge_bit[5:4]",\
" ",\
"reg_buck_02_vref_fast_charge_bit[3:2]",\
" ",\
"reg_buck_01_vref_fast_charge_bit[1:0]",\
" ",\
},\
{0x382,\
0x0000,\
" ",\
" ",\
"reg_ldo_05_en_ocp",\
"reg_ldo_05_en_active_disc",\
"reg_ldo_05_drv_sel",\
"reg_ldo_05_active_dis_sel[10:9]",\
" ",\
"reg_buck_05_cal_deltav[8:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x383,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_vcomp_cal2_en",\
"reg_buck_05_vcomp_cal2_en",\
"reg_buck_04_vcomp_cal2_en",\
"reg_buck_03_vcomp_cal2_en",\
"reg_buck_02_vcomp_cal2_en",\
"reg_buck_01_vcomp_cal2_en",\
"reg_ldo_05_ib2_sel[5:4]",\
" ",\
"reg_ldo_05_ib1_sel[3:2]",\
" ",\
"reg_ldo_05_ib0_sel[1:0]",\
" ",\
},\
{0x384,\
0x0000,\
"reg_buck_04_plimit_trim[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_03_plimit_trim[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_02_plimit_trim[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_01_plimit_trim[3:0]",\
" ",\
" ",\
" ",\
},\
{0x385,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_plimit_trim[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_05_plimit_trim[3:0]",\
" ",\
" ",\
" ",\
},\
{0x386,\
0x0000,\
"reg_buck_04_nlimit_trim[15:12]",\
" ",\
" ",\
" ",\
"reg_buck_03_nlimit_trim[11:8]",\
" ",\
" ",\
" ",\
"reg_buck_02_nlimit_trim[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_01_nlimit_trim[3:0]",\
" ",\
" ",\
" ",\
},\
{0x387,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_06_nlimit_trim[7:4]",\
" ",\
" ",\
" ",\
"reg_buck_05_nlimit_trim[3:0]",\
" ",\
" ",\
" ",\
},\
{0x388,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_02_pblock_auto[8:5]",\
" ",\
" ",\
" ",\
"reg_buck_02_nblock_auto[4:1]",\
" ",\
" ",\
" ",\
"reg_buck_02_en_block_auto",\
},\
{0x389,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_03_pblock_auto[8:5]",\
" ",\
" ",\
" ",\
"reg_buck_03_nblock_auto[4:1]",\
" ",\
" ",\
" ",\
"reg_buck_03_en_block_auto",\
},\
{0x38a,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_05_pblock_auto[8:5]",\
" ",\
" ",\
" ",\
"reg_buck_05_nblock_auto[4:1]",\
" ",\
" ",\
" ",\
"reg_buck_05_en_block_auto",\
},\
{0x38b,\
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
"reg_buck_04_en_block_auto",\
},\
{0x38c,\
0x0000,\
"reg_buck_04_pblock_auto[15:8]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_buck_04_nblock_auto[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
}\
}