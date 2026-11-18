//This file defined cc register address and it`s meaning on very bit
//
//
#define cc_reg_total_num 82

typedef struct {
    int    cc_address;
    int    defaul_value;
    char   *cc_register_define_bit_meaing[16];
} CC_Register_ST;

#define cc_value_default {\
{0x0,\
0x0000,\
" ",\
" ",\
" ",\
"revid[3:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"chipid[15:4]",\
},\
{0x2,\
0x0000,\
" ",\
" ",\
" ",\
"vadc_rd_int",\
"iadc_rd_int",\
" ",\
" ",\
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
{0x3,\
0x0000,\
"reg_cc_ck_in_dr",\
"reg_cc_ck_in",\
" ",\
" ",\
"reg_cc_ibias_en_dr",\
"reg_cc_ibias_en",\
"reg_cc_rstn_dr",\
"reg_cc_rstn",\
" ",\
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
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_cc_reserved[15:0]",\
},\
{0x10,\
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
{0x1c,\
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
"cfg_clk_cc_vadc_inv",\
"cfg_clk_cc_iadc_inv",\
" ",\
" ",\
" ",\
},\
{0x30,\
0x0000,\
"reg_cc_ck_edge_sel",\
" ",\
"reg_cc_fch_op_sel[2:1]",\
" ",\
" ",\
" ",\
"reg_cc_fch_vrefbuf_sel[6:5]",\
" ",\
" ",\
" ",\
"reg_cc_clk_sel",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x31,\
0x0000,\
"reg_cc_iadc_en_refresh_vrefbuf",\
" ",\
" ",\
"reg_cc_iadc_lp_vrefbuf[3:1]",\
"reg_cc_iadc_op1_csel",\
" ",\
"reg_cc_iadc_op1_isel[6:5]",\
"reg_cc_iadc_pu_ch_op",\
"reg_cc_iadc_pu_ch_sys",\
" ",\
" ",\
" ",\
"reg_cc_iadc_res_vrefbuf[12:10]",\
"reg_cc_iadc_vrefp_sel",\
" ",\
" ",\
},\
{0x32,\
0x0000,\
" ",\
" ",\
" ",\
"reg_cc_iadc_cap_vrefbuf[3:0]",\
"reg_cc_iadc_cko_edge_sel",\
" ",\
" ",\
" ",\
"reg_cc_iadc_drv_vrefbuf[8:5]",\
"dig_cc_iadc_dout",\
"cc_pu_ck_dr",\
"reg_cc_pu_ck",\
" ",\
" ",\
" ",\
" ",\
},\
{0x33,\
0x0000,\
"reg_iadc_cc_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_cc_iadc_en_cnt[13:2]",\
"reg_iadc_sleep_mode",\
" ",\
},\
{0x34,\
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
"reg_cc_iadc_filte_en_cnt[10:0]",\
"dig_cc_iadc_en_dr",\
" ",\
"reg_cc_iadc_en",\
"cc_iadc_filte_en_dr",\
"reg_cc_iadc_filte_en",\
},\
{0x35,\
0x0000,\
"resetn_iadc_filter_dr",\
" ",\
"cc_iadc_rstn_dr",\
"reg_cc_iadc_rstn",\
"reg_iadc_coi_filte_enable",\
"iadc_coi_filte_enable_dr",\
" ",\
" ",\
" ",\
" ",\
"reg_iadc_coi_filte_delay[10:6]",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x36,\
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
"reg_iadc_coi_filte_osr[11:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x42,\
0x0000,\
"iadc_fifo_wr_clk_dr",\
"iadc_fifo_rd_clk_dr",\
"iadc_fifo_clk_dr",\
"iadc_fifo_rd_direction_reg",\
"iadc_fifo_rd_start_reg",\
"iadc_resetn_fifo_reg",\
"cfg_iadc_fifo_wr_pol",\
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
{0x43,\
0x0000,\
"iadc_fifo_reg_wr_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
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
{0x44,\
0x0000,\
"iadc_fifo_rd_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
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
{0x45,\
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
"iadc_fifo_in_lo[15:0]",\
},\
{0x47,\
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
"iadc_fifo_in_hi[11:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x48,\
0x0000,\
" ",\
" ",\
"iadc_ema[2:0]",\
" ",\
"iadc_emaw[4:3]",\
"iadc_emas",\
"iadc_wabl",\
" ",\
"iadc_wablm[8:7]",\
"iadc_rawl",\
" ",\
"iadc_rawlm[11:10]",\
"iadc_pgen",\
"iadc_ret1n",\
"iadc_ret2n",\
" ",\
},\
{0x49,\
0x0000,\
"iadc_addr_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"iadc_addr_reg[7:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"iadc_fifo_data_num_th[14:8]",\
" ",\
},\
{0x4a,\
0x0000,\
"iadc_wr_ptr_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"iadc_wr_addr_ptr_reg[8:1]",\
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
"iadc_rd_ptr_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"iadc_rd_addr_ptr_reg[8:1]",\
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
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"iadc_fifo_out_lo[15:0]",\
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
"iadc_fifo_out_hi[11:0]",\
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
"iadc_addr[6:0]",\
"iadc_all_fifo_data_vld_flag",\
" ",\
" ",\
"iadc_state[10:8]",\
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
"iadc_wr_addr_ptr[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"iadc_rd_addr_ptr[15:8]",\
},\
{0x50,\
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
"iadc_filter_out_int_coi_lo[15:0]",\
},\
{0x51,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"iadc_filter_out_int_coi_hi[7:0]",\
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
"reg_cc_vadc_cap_vrefbuf[3:0]",\
"reg_cc_vadc_cko_edge_sel",\
" ",\
" ",\
" ",\
" ",\
"reg_cc_vadc_en_dem",\
" ",\
" ",\
" ",\
"reg_cc_vadc_lp_vrefbuf[13:11]",\
"reg_cc_vadc_op1_csel",\
" ",\
},\
{0x61,\
0x0000,\
" ",\
"reg_cc_vadc_op1_isel[1:0]",\
"reg_cc_vadc_pu_ch_op",\
"reg_cc_vadc_pu_ch_sys",\
" ",\
" ",\
" ",\
"reg_cc_vadc_res_vrefbuf[7:5]",\
"dig_cc_vadc_dout",\
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
"reg_vadc_cc_en",\
"reg_vadc_chan_sel_init",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_cc_vadc_en_cnt[13:2]",\
"reg_vadc_sleep_mode",\
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
" ",\
" ",\
" ",\
"reg_cc_vadc_filte_en_cnt[10:0]",\
"cc_vadc_en_dr",\
"dig_cc_vadc_en_dr",\
"reg_cc_vadc_en",\
"cc_vadc_filte_en_dr",\
"reg_cc_vadc_filte_en",\
},\
{0x64,\
0x0000,\
"resetn_vadc_filter_dr",\
" ",\
"cc_vadc_rstn_dr",\
"reg_cc_vadc_rstn",\
"reg_vadc_coi_filte_enable",\
"vadc_coi_filte_enable_dr",\
" ",\
" ",\
" ",\
" ",\
"reg_vadc_coi_filte_delay[10:6]",\
"reg_vadc_single_chan_mode",\
"vadc_sleep_en_dr",\
"reg_vadc_sleep_en",\
"cc_vadc_chan_sel_dr",\
"reg_cc_vadc_chan_sel",\
},\
{0x65,\
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
"reg_vadc_coi_filte_osr[11:0]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x66,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vadc_ch0_sample_point[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_vadc_ch1_sample_point[15:8]",\
},\
{0x67,\
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
"reg_vadc_sleep_time[15:0][15:0]",\
},\
{0x68,\
0x0000,\
" ",\
" ",\
"reg_vadc_sleep_time[18:16][2:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"cc_vadc_fsm_en_dr",\
"reg_cc_vadc_fsm_en",\
"dig_cc_conversion_done_dr",\
"reg_cc_conversion_done",\
" ",\
},\
{0x74,\
0x0000,\
"vadc_fifo_wr_clk_dr",\
"vadc_fifo_rd_clk_dr",\
"vadc_fifo_clk_dr",\
"vadc_fifo_rd_direction_reg",\
"vadc_fifo_rd_start_reg",\
"vadc_resetn_fifo_reg",\
"cfg_vadc_fifo_wr_pol",\
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
{0x75,\
0x0000,\
"vadc_fifo_reg_wr_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
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
{0x76,\
0x0000,\
"vadc_fifo_rd_en",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
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
{0x77,\
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
"vadc_fifo_in_lo[15:0]",\
},\
{0x78,\
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
"vadc_fifo_in_hi[11:0]",\
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
" ",\
"vadc_fifo_data_num_th[6:0]",\
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
" ",\
"vadc_ema[2:0]",\
" ",\
"vadc_emaw[4:3]",\
"vadc_emas",\
"vadc_wabl",\
" ",\
"vadc_wablm[8:7]",\
"vadc_rawl",\
" ",\
"vadc_rawlm[11:10]",\
"vadc_pgen",\
"vadc_ret1n",\
"vadc_ret2n",\
" ",\
},\
{0x7b,\
0x0000,\
"vadc_addr_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"vadc_addr_reg[7:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x7c,\
0x0000,\
"vadc_wr_ptr_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"vadc_wr_addr_ptr_reg[8:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x7d,\
0x0000,\
"vadc_rd_ptr_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"vadc_rd_addr_ptr_reg[8:1]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x7e,\
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
"vadc_fifo_out_lo[15:0]",\
},\
{0x7f,\
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
"vadc_fifo_out_hi[11:0]",\
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
" ",\
" ",\
" ",\
"vadc_addr[6:0]",\
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
"vadc_all_fifo_data_vld_flag",\
" ",\
"vadc_cc_vadc_done",\
" ",\
" ",\
"vadc_state[5:3]",\
"vadc_cc_vadc_filte_en_fsm",\
"vadc_sleep_en_fsm",\
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
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"vadc_filter_out_int_coi_lo[15:0]",\
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
"vadc_filter_out_int_coi_hi[7:0]",\
" ",\
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
"vadc_wr_addr_ptr[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"vadc_rd_addr_ptr[15:8]",\
},\
{0x86,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"iadc_fifo_data_avail[7:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"vadc_fifo_data_avail[15:8]",\
},\
{0x87,\
0x0000,\
"iadc_rd_int_clr_reg",\
"iadc_rd_int_mask",\
"iadc_rd_int_raw_en_reg",\
"iadc_rd_int_raw",\
"vadc_rd_int_clr_reg",\
"vadc_rd_int_mask",\
"vadc_rd_int_raw_en_reg",\
"vadc_rd_int_raw",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x88,\
0x0000,\
"reg_cc_bg2_en_dr",\
"reg_cc_bg2_en_chop",\
"reg_cc_bg2_en",\
"reg_cc_bg2_en_notch",\
" ",\
" ",\
" ",\
"reg_cc_bg2_res_sel[7:4]",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_cc_ibias_sel",\
" ",\
},\
{0x89,\
0x0000,\
" ",\
"reg_cc_ibias_isel[1:0]",\
" ",\
"reg_cc_ibias_sel_bg2[3:2]",\
" ",\
"reg_cc_ibias_sel_iadc_op1[5:4]",\
" ",\
"reg_cc_ibias_sel_iadc_op2[7:6]",\
" ",\
"reg_cc_ibias_sel_iadc_vcmbuf[9:8]",\
" ",\
"reg_cc_ibias_sel_iadc_vrefbuf[11:10]",\
" ",\
"reg_cc_ibias_sel_vadc_op1[13:12]",\
" ",\
"reg_cc_ibias_sel_vadc_op2[15:14]",\
},\
{0x8a,\
0x0000,\
" ",\
"reg_cc_ibias_sel_vadc_vrefbuf[1:0]",\
" ",\
" ",\
" ",\
" ",\
" ",\
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
"reg_ch_done_dly_cnt[3:0]",\
" ",\
" ",\
" ",\
"reg_vadc_coi_resetn_cnt[7:4]",\
" ",\
" ",\
" ",\
"reg_vadc_coi_ch0_sys_cnt[11:8]",\
" ",\
" ",\
" ",\
"reg_vadc_coi_ch1_sys_cnt[15:12]",\
},\
{0x8c,\
0x0000,\
"reg_vadc_fifo_raw_data",\
"reg_vadc_data_add_mode",\
"reg_vadc_data_sub_mode",\
"dig_cc_vadc_ck_ch0_sys_dr",\
"reg_cc_vadc_ck_ch0_sys",\
"reg_cc_vadc_ck_ch0_sys_inv",\
"dig_cc_vadc_os_ch0_cal_sel_dr",\
"reg_cc_vadc_os_ch0_cal_sel",\
"reg_cc_vadc_os_ch0_cal_sel_inv",\
"dig_cc_vadc_ck_ch1_sys_dr",\
"reg_cc_vadc_ck_ch1_sys",\
"reg_cc_vadc_ck_ch1_sys_inv",\
"dig_cc_vadc_os_ch1_cal_sel_dr",\
"reg_cc_vadc_os_ch1_cal_sel",\
"reg_cc_vadc_os_ch1_cal_sel_inv",\
" ",\
},\
{0x8d,\
0x0000,\
"reg_iadc_fifo_raw_data",\
"reg_iadc_data_add_mode",\
"reg_iadc_data_sub_mode",\
"dig_cc_iadc_ck_ch_sys_dr",\
"reg_cc_iadc_ck_ch_sys",\
"reg_cc_iadc_ck_ch_sys_inv",\
"dig_cc_iadc_os_ch_cal_sel_dr",\
"reg_cc_iadc_os_ch_cal_sel",\
"reg_cc_iadc_os_ch_cal_sel_inv",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x8e,\
0x0000,\
" ",\
" ",\
" ",\
"reg_iadc_ch_done_dly_cnt[3:0]",\
" ",\
" ",\
" ",\
"reg_iadc_coi_resetn_cnt[7:4]",\
" ",\
" ",\
" ",\
"reg_iadc_coi_ch_sys_cnt[11:8]",\
" ",\
" ",\
" ",\
" ",\
},\
{0x8f,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_iadc_ch_sample_point[7:0]",\
"reg_iadc_sleep_en",\
"iadc_sleep_en_dr",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
},\
{0x90,\
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
"reg_iadc_sleep_time[15:0][15:0]",\
},\
{0x91,\
0x0000,\
" ",\
" ",\
"reg_iadc_sleep_time[18:16][2:0]",\
" ",\
" ",\
" ",\
" ",\
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
{0xa0,\
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
"reg_efuse_burn_a0[15:0]",\
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
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_burn_a1[15:0]",\
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
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_efuse_burn_a2[15:0]",\
},\
{0xa3,\
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
"reg_efuse_burn_a3[15:0]",\
},\
{0xa4,\
0x0000,\
"reg_efuse_cs",\
"reg_efuse_cs_dr",\
"reg_efuse_pgm",\
"reg_efuse_pgm_dr",\
"reg_efuse_pu_avdd",\
"reg_efuse_pu_avdd_dr",\
"reg_efuse_pu_dvdd",\
"reg_efuse_pu_dvdd_dr",\
"reg_efuse_rw",\
"reg_efuse_rw_dr",\
"reg_efuse_sclk",\
"reg_efuse_sclk_dr",\
"reg_efuse_clk_fast_sel",\
"reg_cc_efuse_clk_1m_en",\
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
"reg_dvdd_time[6:0]",\
" ",\
" ",\
" ",\
" ",\
"reg_addr_hold_time[11:8]",\
" ",\
" ",\
" ",\
"reg_addr_setup_time[15:12]",\
},\
{0xa6,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_avdd_time[6:0]",\
" ",\
" ",\
" ",\
" ",\
"reg_bit_switch_time[11:8]",\
" ",\
" ",\
" ",\
"reg_cs_time[15:12]",\
},\
{0xa7,\
0x0000,\
" ",\
" ",\
" ",\
" ",\
" ",\
" ",\
"reg_pgm_time[6:0]",\
" ",\
" ",\
" ",\
" ",\
"reg_rdata_time[11:8]",\
" ",\
" ",\
" ",\
"reg_rw_time[15:12]",\
},\
{0xa8,\
0x0000,\
"reg_efuse_on",\
"reg_pgm_sel",\
"reg_efuse_clk_sel",\
" ",\
" ",\
" ",\
" ",\
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
{0xa9,\
0x0000,\
"efuse_end",\
" ",\
" ",\
" ",\
"dbg_efuse_status[4:1]",\
"efuse_ctrl_pin",\
" ",\
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
{0xaa,\
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
"efuse_read_data[15:0][15:0]",\
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
" ",\
" ",\
" ",\
"efuse_read_data[31:16][15:0]",\
},\
{0xac,\
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
"efuse_read_data[47:32][15:0]",\
},\
{0xad,\
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
"efuse_read_data[63:48][15:0]",\
},\
{0xae,\
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
"vadc_first_data[15:0][15:0]",\
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
"vadc_first_data[27:16][11:0]",\
" ",\
" ",\
" ",\
" ",\
}\
}