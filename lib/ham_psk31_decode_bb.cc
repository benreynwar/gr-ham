/* -*- c++ -*- */
/* 
 * Copyright 2012 Free Software Foundation
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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gr_io_signature.h>
#include <ham_psk31_decode_bb.h>
#include <iostream>

ham_psk31_decode_bb_sptr
ham_make_psk31_decode_bb (bool bit_flip)
{
	return ham_psk31_decode_bb_sptr (new ham_psk31_decode_bb (bit_flip));
}


ham_psk31_decode_bb::ham_psk31_decode_bb (bool bit_flip)
	: gr_block ("decode_bb",
		gr_make_io_signature (1, 1, sizeof (unsigned char)),
		gr_make_io_signature (1, 1, sizeof (unsigned char)))
{
  // Make a lookup mapping for varicodes.
  for (unsigned int i=0; i<128; i++) {
	psk31_map[psk31_varicodes[i]] = i;
  }
  d_bit_flip = bit_flip;
  d_last_zero = true;
  d_current_bits = 0;
}


ham_psk31_decode_bb::~ham_psk31_decode_bb ()
{
}


int
ham_psk31_decode_bb::general_work (int noutput_items,
			       gr_vector_int &ninput_items,
			       gr_vector_const_void_star &input_items,
			       gr_vector_void_star &output_items)
{
  unsigned char const *in = (const unsigned char *) input_items[0];
  unsigned char *out = (unsigned char *) output_items[0];
  int i = 0;
  int j = 0;
  unsigned char next_bit;
  while((i < noutput_items) && (j < ninput_items[0])) {
	next_bit = in[j++];
	if (d_bit_flip) {
	  next_bit = (next_bit + 1) % 2;
	}
	if (d_last_zero) {
	  if (!next_bit) {
		d_last_zero = true;
		// We have '00' so output symbol.
		if (d_current_bits) {
		  if (d_current_bits >= 4096) {
			out[i++] = '?';
		  } else {
			unsigned char symbol = psk31_map[d_current_bits];
			if (symbol >= 128) {
				out[i++] = '?';
			  } else {
			  out[i++] = symbol;
			}
		  }
		  d_current_bits = 0;
		}
	  } else {
		d_last_zero = false;
		// Add '01' to the end of the current_bits
		d_current_bits = d_current_bits << 2;
		d_current_bits += 1;
	  }
	} else {
	  if (!next_bit) {
		d_last_zero = true;
	  } else {
		d_last_zero = false;
		// Add '1' to the end of the current_bits
		d_current_bits = d_current_bits << 1;
		d_current_bits += 1;
	  }
	}
  }

  consume_each(j);
  return i;
}

