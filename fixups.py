import os

def rw(p, fn):
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    s2 = fn(s)
    if s2 != s:
        open(p, "w", encoding="utf-8", errors="surrogateescape").write(s2)
        print("patched", p)
    else:
        print("skip", p)

# 1) fs/exec.c
rw("fs/exec.c", lambda s: s if "linux/susfs_def.h" in s else s.replace(
    "#include <linux/coredump.h>",
    "#include <linux/coredump.h>\n#include <linux/susfs_def.h>", 1))

# 2) fs/namespace.c
def f_ns(s):
    if "linux/susfs_def.h" in s:
        return s
    blk = ("#ifdef CONFIG_KSU_SUSFS\n#include <linux/susfs_def.h>\n#endif\n"
           "#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n"
           "extern bool susfs_is_current_ksu_domain(void);\n"
           "extern struct static_key_true susfs_is_sdcard_android_data_not_decrypted;\n"
           "#define CL_COPY_MNT_NS BIT(25)\n#endif\n")
    for anchor in ['#include "internal.h"', '#include "pnode.h"']:
        if anchor in s:
            return s.replace(anchor, blk + anchor, 1)
    return s
rw("fs/namespace.c", f_ns)

# 3) fs/Makefile
rw("fs/Makefile", lambda s: s if "susfs.o" in s else s + "\nobj-$(CONFIG_KSU_SUSFS) += susfs.o\n")

# 4) fs/proc/task_mmu.c show_smap
def f_mmu(s):
    marker = "struct mem_size_stats mss;\n\n#ifdef CONFIG_KSU_SUSFS_SUS_MAP"
    if marker in s:
        return s
    anchor = ("static int show_smap(struct seq_file *m, void *v)\n{\n"
              "\tstruct vm_area_struct *vma = v;\n\tstruct mem_size_stats mss;\n")
    add = anchor + ("\n#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n\tif (vma->vm_file) {\n"
                    "\t\tif (SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file)))\n"
                    "\t\t\treturn 0;\n\t}\n#endif\n")
    return s.replace(anchor, add, 1)
rw("fs/proc/task_mmu.c", f_mmu)
