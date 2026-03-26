#!/bin/bash
# Package the Q-Day submission for the public GitHub repo
# Run this from the Patent-HexagalPairty- directory
#
# Usage: bash submission/PACKAGE_FOR_GITHUB.sh /path/to/public-repo
#
# This copies ONLY the safe-to-publish files. No G.O.D. Engine, no patents.

set -e

TARGET=${1:-"../qday-public-submission"}

echo "Packaging Q-Day submission to: $TARGET"
mkdir -p "$TARGET"

# Submission docs
cp submission/README.md "$TARGET/"
cp submission/SUBMISSION_WRITEUP.md "$TARGET/"
cp submission/LICENSE "$TARGET/"

# Core quantum code (safe — standard Shor's, no IP)
mkdir -p "$TARGET/quantum_btc_qday"
for f in __init__.py shor_ecdlp.py ecc_curves.py quantum_arithmetic.py \
         ecc_point_oracle.py attack_pipeline.py run_qday_attack.py \
         run_ibm_quantum.py requirements.txt QDAY_SUBMISSION.md; do
    cp "quantum_btc_qday/$f" "$TARGET/quantum_btc_qday/"
done

# Results
cp -r qday_results "$TARGET/"

# Image (add manually — save dialectical_moire_engine.png to $TARGET/)
echo ""
echo "DONE. Files packaged to: $TARGET"
echo ""
echo "REMINDER: Save the Dialectical Moire Engine image as:"
echo "  $TARGET/dialectical_moire_engine.png"
echo ""
echo "Then: cd $TARGET && git add -A && git commit && git push"
