locals {
  tmpf_kms_keys  =  "${join("\",\"",var.kms_keys)}"
}