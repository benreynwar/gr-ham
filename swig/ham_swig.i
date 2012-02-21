/* -*- c++ -*- */

#define HAM_API

%include "gnuradio.i"			// the common stuff

//load generated python docstrings
%include "ham_swig_doc.i"

%{
#include "ham_psk31_decode_bb.h"
%}

#if SWIGGUILE
%scheme %{
(load-extension-global "libguile-gnuradio-ham_swig" "scm_init_gnuradio_ham_swig_module")
%}

%goops %{
(use-modules (gnuradio gnuradio_core_runtime))
%}
#endif
GR_SWIG_BLOCK_MAGIC(ham,psk31_decode_bb);
%include "ham_psk31_decode_bb.h"
