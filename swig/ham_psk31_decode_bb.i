GR_SWIG_BLOCK_MAGIC(ham, Psk31_decode_bb)

ham_psk31_decode_bb_sptr 
ham_make_psk31_decode_bb (bool bit_flip);

class ham_psk31_decode_bb : public gr_block
{
 private:
  ham_psk31_decode_bb (bool bit_flip);

  friend ham_psk31_decode_bb_sptr 
  	ham_make_psk31_decode_bb (bool bit_flip);

 public:
  ~ham_psk31_decode_bb();
};
