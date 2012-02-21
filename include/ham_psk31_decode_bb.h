/* -*- c++ -*- */
/* 
 * Copyright 2012 Free Software Foundation.
 * 
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 * 
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifndef INCLUDED_HAM_PSK31_DECODE_BB_H
#define INCLUDED_HAM_PSK31_DECODE_BB_H

#include <ham_api.h>
#include <gr_block.h>

class ham_psk31_decode_bb;
typedef boost::shared_ptr<ham_psk31_decode_bb> ham_psk31_decode_bb_sptr;

HAM_API ham_psk31_decode_bb_sptr ham_make_psk31_decode_bb (bool bit_flip);

/*!
 * \brief This block decodes a bitstream assuming psk31 coding.
 * \ingroup ham
 *
 * The variable length coding used in psk31 is described in
 * http://aintel.bi.ehu.es/psk31.html.
 *
 */
class HAM_API ham_psk31_decode_bb : public gr_block
{
	friend HAM_API ham_psk31_decode_bb_sptr ham_make_psk31_decode_bb (bool bit_flip);

	ham_psk31_decode_bb (bool bit_flip);

 public:
	~ham_psk31_decode_bb ();


  int general_work (int noutput_items,
		    gr_vector_int &ninput_items,
		    gr_vector_const_void_star &input_items,
		    gr_vector_void_star &output_items);

 private:
  unsigned char psk31_map[4096];
  bool d_last_zero;
  unsigned int d_current_bits;
  bool d_bit_flip;
};

unsigned short psk31_varicodes[128] = {
  683, 731, 749, 887, 747, 863, 751, 765, 767, 239, 29, 879, 733, 31, 885, 939,
  759, 757, 941, 943, 859, 875, 877, 855, 891, 893, 951, 853, 861, 955, 763, 895,
  1, 511, 351, 501, 475, 725, 699, 383, 251, 247, 367, 479, 117, 53, 87, 431,
  183, 189, 237, 255, 375, 347, 363, 429, 427, 439, 245, 445, 493, 85, 471, 687,
  701, 125, 235, 173, 181, 119, 219, 253, 341, 127, 509, 381, 215, 187, 221, 171,
  213, 477, 175, 111, 109, 343, 437, 349, 373, 379, 685, 503, 495, 507, 703, 365,
  735, 11, 95, 47, 45, 3, 61, 91, 43, 13, 491, 191, 27, 59, 15, 7,
  63, 447, 21, 23, 5, 55, 123, 107, 223, 93, 469, 695, 443, 693, 727, 949/*,
  957, 959, 981, 983, 987, 989, 991, 1003, 1005, 1007, 1013, 1015, 1019, 1021, 1023, 1365,
  1367, 1371, 1373, 1375, 1387, 1389, 1391, 1397, 1399, 1403, 1405, 1407, 1451, 1453, 1455, 1461,
  1463, 1467, 1469, 1471, 1493, 1495, 1499, 1501, 1503, 1515, 1517, 1519, 1525, 1527, 1531, 1533,
  1535, 1707, 1709, 1711, 1717, 1719, 1723, 1725, 1727, 1749, 1751, 1755, 1757, 1759, 1771, 1773,
  1775, 1781, 1783, 1787, 1789, 1791, 1877, 1879, 1883, 1885, 1887, 1899, 1901, 1903, 1909, 1911,
  1915, 1917, 1919, 1963, 1965, 1967, 1973, 1975, 1979, 1981, 1983, 2005, 2007, 2011, 2013, 2015,
  2027, 2029, 2031, 2037, 2039, 2043, 2045, 2047, 2731, 2733, 2735, 2741, 2743, 2747, 2749, 2751,
  2773, 2775, 2779, 2781, 2783, 2795, 2797, 2799, 2805, 2807, 2811, 2813, 2815, 2901, 2903, 2907 */
};
  
#endif /* INCLUDED_HAM_PSK31_DECODE_BB_H */

