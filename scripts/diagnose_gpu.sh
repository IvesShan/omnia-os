#!/bin/bash
# GPU 诊断脚本

echo "=== GPU 诊断 ==="
echo ""

echo "1. 检查 ROCm 设备:"
rocminfo 2>/dev/null | grep -E "Name:|Marketing Name:" | grep -A1 "gfx1030"
echo ""

echo "2. 检查设备权限:"
ls -la /dev/kfd /dev/dri/renderD* 2>/dev/null
echo ""

echo "3. 检查用户组:"
groups | grep -o "render\|video"
echo ""

echo "4. 检查 ROCm 库:"
ldconfig -p | grep -E "libhipblas|librocblas" | head -3
echo ""

echo "5. 测试简单 HIP 程序:"
cat > /tmp/hip_test.cpp << 'EOF'
#include <hip/hip_runtime.h>
#include <iostream>

int main() {
    int deviceCount;
    hipGetDeviceCount(&deviceCount);
    std::cout << "HIP 设备数量: " << deviceCount << std::endl;
    
    if (deviceCount > 0) {
        hipDeviceProp_t prop;
        hipGetDeviceProperties(&prop, 0);
        std::cout << "设备 0: " << prop.name << std::endl;
        std::cout << "显存: " << prop.totalGlobalMem / 1024 / 1024 << " MB" << std::endl;
    }
    
    return 0;
}
EOF

export HSA_OVERRIDE_GFX_VERSION=10.3.0
/opt/rocm-6.2.0/bin/hipcc /tmp/hip_test.cpp -o /tmp/hip_test 2>/dev/null
/tmp/hip_test 2>&1
rm -f /tmp/hip_test /tmp/hip_test.cpp
echo ""

echo "6. 测试 llama.cpp GPU 支持:"
export HSA_OVERRIDE_GFX_VERSION=10.3.0
export LD_LIBRARY_PATH=/opt/rocm-6.2.0/lib:$LD_LIBRARY_PATH
/home/shan/llama.cpp/build/bin/llama-cli --help 2>&1 | grep -i "gpu\|cuda\|rocm" | head -5
echo ""

echo "=== 诊断完成 ==="
