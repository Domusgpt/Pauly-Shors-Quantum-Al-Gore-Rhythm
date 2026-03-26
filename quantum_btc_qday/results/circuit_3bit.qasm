OPENQASM 2.0;
include "qelib1.inc";
gate mcphase(param0) q0,q1,q2,q3,q4,q5,q6 { h q6; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q6; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q6; p(-pi/8) q6; cx q1,q6; p(pi/8) q6; cx q2,q6; p(-pi/8) q6; cx q0,q6; p(pi/8) q6; cx q2,q6; p(-pi/8) q6; cx q1,q6; p(pi/8) q6; cx q2,q6; p(-pi/8) q6; cx q0,q6; h q6; rz(-pi/4) q6; h q6; p(pi/8) q3; p(pi/8) q4; p(pi/8) q5; p(pi/8) q6; cx q3,q4; p(-pi/8) q4; cx q3,q4; cx q4,q5; p(-pi/8) q5; cx q3,q5; p(pi/8) q5; cx q4,q5; p(-pi/8) q5; cx q3,q5; cx q5,q6; p(-pi/8) q6; cx q4,q6; p(pi/8) q6; cx q5,q6; p(-pi/8) q6; cx q3,q6; p(pi/8) q6; cx q5,q6; p(-pi/8) q6; cx q4,q6; p(pi/8) q6; cx q5,q6; p(-pi/8) q6; cx q3,q6; h q6; rz(pi/4) q6; h q6; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q6; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q6; p(-pi/8) q6; cx q1,q6; p(pi/8) q6; cx q2,q6; p(-pi/8) q6; cx q0,q6; p(pi/8) q6; cx q2,q6; p(-pi/8) q6; cx q1,q6; p(pi/8) q6; cx q2,q6; p(-pi/8) q6; cx q0,q6; h q6; rz(-pi/4) q6; h q6; p(pi/8) q3; p(pi/8) q4; p(pi/8) q5; p(pi/8) q6; cx q3,q4; p(-pi/8) q4; cx q3,q4; cx q4,q5; p(-pi/8) q5; cx q3,q5; p(pi/8) q5; cx q4,q5; p(-pi/8) q5; cx q3,q5; cx q5,q6; p(-pi/8) q6; cx q4,q6; p(pi/8) q6; cx q5,q6; p(-pi/8) q6; cx q3,q6; p(pi/8) q6; cx q5,q6; p(-pi/8) q6; cx q4,q6; p(pi/8) q6; cx q5,q6; p(-pi/8) q6; cx q3,q6; h q6; rz(pi/4) q6; h q5; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q5; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q5; p(-pi/8) q5; cx q1,q5; p(pi/8) q5; cx q2,q5; p(-pi/8) q5; cx q0,q5; p(pi/8) q5; cx q2,q5; p(-pi/8) q5; cx q1,q5; p(pi/8) q5; cx q2,q5; p(-pi/8) q5; cx q0,q5; h q5; rz(-pi/8) q5; h q5; cx q4,q5; tdg q5; cx q3,q5; t q5; cx q4,q5; tdg q5; cx q3,q5; t q4; t q5; h q5; cx q3,q4; t q3; tdg q4; cx q3,q4; rz(pi/8) q5; h q5; p(pi/8) q0; p(pi/8) q1; p(pi/8) q2; p(pi/8) q5; cx q0,q1; p(-pi/8) q1; cx q0,q1; cx q1,q2; p(-pi/8) q2; cx q0,q2; p(pi/8) q2; cx q1,q2; p(-pi/8) q2; cx q0,q2; cx q2,q5; p(-pi/8) q5; cx q1,q5; p(pi/8) q5; cx q2,q5; p(-pi/8) q5; cx q0,q5; p(pi/8) q5; cx q2,q5; p(-pi/8) q5; cx q1,q5; p(pi/8) q5; cx q2,q5; p(-pi/8) q5; cx q0,q5; h q5; rz(-pi/8) q5; h q5; cx q4,q5; tdg q5; cx q3,q5; t q5; cx q4,q5; tdg q5; cx q3,q5; t q4; t q5; h q5; cx q3,q4; t q3; tdg q4; cx q3,q4; rz(pi/8) q5; h q4; cx q1,q4; tdg q4; cx q0,q4; t q4; cx q1,q4; tdg q4; cx q0,q4; t q1; t q4; h q4; cx q0,q1; t q0; tdg q1; cx q0,q1; rz(-pi/16) q4; h q4; cx q3,q4; tdg q4; cx q2,q4; t q4; cx q3,q4; tdg q4; cx q2,q4; t q3; t q4; h q4; cx q2,q3; t q2; tdg q3; cx q2,q3; rz(pi/16) q4; h q4; cx q1,q4; tdg q4; cx q0,q4; t q4; cx q1,q4; tdg q4; cx q0,q4; t q1; t q4; h q4; cx q0,q1; t q0; tdg q1; cx q0,q1; rz(-pi/16) q4; h q4; cx q3,q4; tdg q4; cx q2,q4; t q4; cx q3,q4; tdg q4; cx q2,q4; t q3; t q4; h q4; cx q2,q3; t q2; tdg q3; cx q2,q3; rz(pi/16) q4; h q3; cx q1,q3; tdg q3; cx q0,q3; t q3; cx q1,q3; tdg q3; cx q0,q3; t q1; t q3; h q3; cx q0,q1; t q0; tdg q1; cx q0,q1; rz(-pi/32) q3; cx q2,q3; rz(pi/32) q3; h q3; cx q1,q3; tdg q3; cx q0,q3; t q3; cx q1,q3; tdg q3; cx q0,q3; t q1; t q3; h q3; cx q0,q1; t q0; tdg q1; cx q0,q1; rz(-pi/32) q3; cx q2,q3; rz(pi/32) q3; cx q0,q2; rz(-pi/64) q2; cx q1,q2; rz(pi/64) q2; cx q0,q2; rz(-pi/64) q2; cx q1,q2; rz(pi/64) q2; crz(pi/32) q0,q1; p(pi/64) q0; }
gate mcx q0,q1,q2,q3,q4,q5,q6 { h q6; mcphase(pi) q0,q1,q2,q3,q4,q5,q6; h q6; }
gate gate_SimplifiedOracle q0,q1,q2,q3,q4,q5,q6,q7,q8 { x q0; x q1; x q2; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q7; x q0; x q1; x q2; x q4; x q5; x q0; x q1; x q2; x q3; x q5; mcx q0,q1,q2,q3,q4,q5,q8; x q0; x q1; x q2; x q3; x q5; x q0; x q1; x q2; x q3; x q4; mcx q0,q1,q2,q3,q4,q5,q7; x q0; x q1; x q2; x q3; x q4; x q0; x q1; x q2; x q4; mcx q0,q1,q2,q3,q4,q5,q8; x q0; x q1; x q2; x q4; x q1; x q2; x q3; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q6; x q1; x q2; x q3; x q4; x q5; x q1; x q2; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q7; x q1; x q2; x q4; x q5; x q1; x q2; x q3; x q5; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q8; x q1; x q2; x q3; x q5; x q1; x q2; x q5; mcx q0,q1,q2,q3,q4,q5,q6; x q1; x q2; x q5; x q1; x q2; x q3; x q4; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q7; x q1; x q2; x q3; x q4; x q1; x q2; x q4; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q8; x q1; x q2; x q4; x q0; x q2; x q3; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q7; x q0; x q2; x q3; x q4; x q5; x q0; x q2; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q8; x q0; x q2; x q4; x q5; x q0; x q2; x q5; mcx q0,q1,q2,q3,q4,q5,q7; x q0; x q2; x q5; x q0; x q2; x q3; x q4; mcx q0,q1,q2,q3,q4,q5,q8; x q0; x q2; x q3; x q4; x q2; x q3; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q7; x q2; x q3; x q4; x q5; x q2; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q8; x q2; x q4; x q5; x q2; x q3; x q5; mcx q0,q1,q2,q3,q4,q5,q6; x q2; x q3; x q5; x q2; x q5; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q7; x q2; x q5; x q2; x q3; x q4; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q8; x q2; x q3; x q4; x q2; x q4; mcx q0,q1,q2,q3,q4,q5,q6; x q2; x q4; x q0; x q1; x q3; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q8; x q0; x q1; x q3; x q4; x q5; x q0; x q1; x q3; x q5; mcx q0,q1,q2,q3,q4,q5,q7; x q0; x q1; x q3; x q5; x q0; x q1; x q5; mcx q0,q1,q2,q3,q4,q5,q8; x q0; x q1; x q5; x q0; x q1; x q4; mcx q0,q1,q2,q3,q4,q5,q7; x q0; x q1; x q4; x q1; x q3; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q8; x q1; x q3; x q4; x q5; x q1; x q4; x q5; mcx q0,q1,q2,q3,q4,q5,q6; x q1; x q4; x q5; x q1; x q3; x q5; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q7; x q1; x q3; x q5; x q1; x q5; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q8; x q1; x q5; x q1; x q3; x q4; mcx q0,q1,q2,q3,q4,q5,q6; x q1; x q3; x q4; x q1; x q4; mcx q0,q1,q2,q3,q4,q5,q6; mcx q0,q1,q2,q3,q4,q5,q7; x q1; x q4; }
gate gate_IQFT q0,q1,q2,q3,q4,q5,q6 { swap q2,q4; swap q1,q5; swap q0,q6; h q0; cp(-pi/2) q1,q0; h q1; cp(-pi/4) q2,q0; cp(-pi/2) q2,q1; h q2; cp(-pi/8) q3,q0; cp(-pi/4) q3,q1; cp(-pi/2) q3,q2; h q3; cp(-pi/16) q4,q0; cp(-pi/8) q4,q1; cp(-pi/4) q4,q2; cp(-pi/2) q4,q3; h q4; cp(-pi/32) q5,q0; cp(-pi/16) q5,q1; cp(-pi/8) q5,q2; cp(-pi/4) q5,q3; cp(-pi/2) q5,q4; h q5; cp(-pi/64) q6,q0; cp(-pi/32) q6,q1; cp(-pi/16) q6,q2; cp(-pi/8) q6,q3; cp(-pi/4) q6,q4; cp(-pi/2) q6,q5; h q6; }
gate gate_IQFT_139851710499408 q0,q1,q2,q3,q4,q5,q6 { gate_IQFT q0,q1,q2,q3,q4,q5,q6; }
gate gate_IQFT_139851661500624 q0,q1,q2,q3,q4,q5,q6 { gate_IQFT q0,q1,q2,q3,q4,q5,q6; }
qreg a[7];
qreg b[7];
qreg oracle_out[3];
creg ca[7];
creg cb[7];
h a[0];
h b[0];
h a[1];
h b[1];
h a[2];
h b[2];
h a[3];
h b[3];
h a[4];
h b[4];
h a[5];
h b[5];
h a[6];
h b[6];
barrier a[0],a[1],a[2],a[3],a[4],a[5],a[6],b[0],b[1],b[2],b[3],b[4],b[5],b[6],oracle_out[0],oracle_out[1],oracle_out[2];
gate_SimplifiedOracle a[0],a[1],a[2],b[0],b[1],b[2],oracle_out[0],oracle_out[1],oracle_out[2];
barrier a[0],a[1],a[2],a[3],a[4],a[5],a[6],b[0],b[1],b[2],b[3],b[4],b[5],b[6],oracle_out[0],oracle_out[1],oracle_out[2];
gate_IQFT_139851710499408 a[0],a[1],a[2],a[3],a[4],a[5],a[6];
gate_IQFT_139851661500624 b[0],b[1],b[2],b[3],b[4],b[5],b[6];
barrier a[0],a[1],a[2],a[3],a[4],a[5],a[6],b[0],b[1],b[2],b[3],b[4],b[5],b[6],oracle_out[0],oracle_out[1],oracle_out[2];
measure a[0] -> ca[0];
measure a[1] -> ca[1];
measure a[2] -> ca[2];
measure a[3] -> ca[3];
measure a[4] -> ca[4];
measure a[5] -> ca[5];
measure a[6] -> ca[6];
measure b[0] -> cb[0];
measure b[1] -> cb[1];
measure b[2] -> cb[2];
measure b[3] -> cb[3];
measure b[4] -> cb[4];
measure b[5] -> cb[5];
measure b[6] -> cb[6];