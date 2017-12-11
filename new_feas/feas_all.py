# coding:utf-8

import pandas as pd
import numpy as np
import os,sys
from multiprocessing import Pool


t_login = pd.read_csv('../datas/t_login.csv')
t_login_test = pd.read_csv('../datas/t_login_test.csv')
t_login = pd.concat([t_login,t_login_test])

t_trade = pd.read_csv('../datas/t_trade.csv')
t_trade_test = pd.read_csv('../datas/t_trade_test.csv')
t_trade_test['is_risk'] = -1
t_trade = pd.concat([t_trade,t_trade_test])

t_trade['trade_stamp'] = t_trade['time'].map(lambda x:pd.to_datetime(x).value//10**9 - 28800.0)
t_trade['hour'] = t_trade['time'].map(lambda x:pd.Timestamp(x).hour)
t_trade['hour_v'] = t_trade['hour'].map(lambda x:x/6)
t_trade['weekday'] = t_trade['time'].map(lambda x:pd.Timestamp(x).date().weekday())
t_trade = t_trade.sort_values('time') \
                .reset_index(drop=True)

# t_login['time'] = t_login['time'].astype(pd.Timestamp)
t_login['timestamp_online'] = t_login['timestamp'] + t_login['timelong']

t_login = t_login.sort_values('time') \
                .reset_index(drop=True)

"""
log_id
timelong
device
log_from
ip
city
result
timestamp
type
id
is_scan
is_sec
time
"""


def baseline_1(idx):
    # TODO 统计这段时间内 ip，device 的登陆失败记录,最长登陆时间记录，用户变动 ip,device 的频次，登陆的频次
    # TODO 两次登陆的时间差，更换 ip,device 的时间差，一段时间内 ip 登陆次数的多少
    # TODO 交易自身的特征,之前的交易次数
    # TODO 对登陆表的特征做的更丰富，再和交易表进行拼接，统计 ip,device 登陆次数，失败次数，扫码次数，安全控件次数

    res = {}
    ida = t_trade.loc[idx]
    res['rowkey'] = ida['rowkey']
    res['is_risk'] = ida['is_risk']
    res['id'] = ida['id']
    res['time'] = ida['time']
    trade_stamp = ida['trade_stamp']
    t = pd.Timestamp(res['time'])

    days30str = str(t - pd.Timedelta(days=30))

    res['hour'] = t.hour
    res['hour_v'] = res['hour'] / 6                                                             # 时间段
    t = t.date()
    res['weekday'] = t.weekday()                                                                # 周信息

    d = t_trade[(t_trade['id'] == id) & (t_trade['time'] >= days30str)]
    res['trade_cnt'] = d.shape[0]                                                               # 交易次数
    res['trade_weekday_cnt'] = d[d['weekday'] == res['weekday']].shape[0]                       # 同一个周几交易次数
    res['trade_weekday_cnt_rate'] = 1.0 * res['trade_weekday_cnt'] / (1 + res['trade_cnt'])
    res['hour_v_cnt'] = d[d['hour_v'] == res['hour_v']].shape[0]                                # 同一个时间段交易次数
    res['hour_v_cnt_rate'] = 1.0 * res['hour_v_cnt'] / (1 + res['trade_cnt'])


    d = t_login[(t_login['time'] < res['time']) &
                         (t_login['time'] >= days30str)]

    # TODO ip 在之前时间内，登陆的次数，登陆的用户数，登陆的时间长度，登陆的城市数，登陆的成功次数
    # TODO id 在之前的时间内，登陆的 ip 次数，device 次数，登陆时间长度，城市数，登陆成功次数
    # TODO ip,id,device,type,city 以及这些的组合，

    login_data = d[(d['id']==res['id'])] \
        .sort_values('time', ascending=False) \
        .reset_index(drop=True)

    login_data1 = login_data[(login_data['result'] == 1)] \
        .sort_values('time', ascending=False) \
        .reset_index(drop=False)

    res['month2_cnt'] = login_data.shape[0]

    # 登陆到交易之间的时间差
    for i in [0,1,2]:
        try:
            res['trade_login_diff{0}'.format(i)] = trade_stamp - login_data1.loc[i]['timestamp']
        except:
            res['trade_login_diff{0}'.format(i)] = None

    for i in [0,1,2]:
        for ci in ['type','result','timelong','log_from']:
            try:
                idx = login_data1.loc[0]['index']
                res[ci + "{0}".format(i)] = login_data.loc[idx+i][ci]
            except:
                res[ci + "{0}".format(i)] = None

        for ci in ['ip','device','id']:
            try:
                idx = login_data1.loc[0]['index']
                idata = login_data.loc[idx+i][ci]

                dci = d[d[ci] == idata]
                dci = dci.sort_values('time', ascending=False) \
                        .reset_index(drop=True)
                for ki in [0, 1]:
                    try:
                        res[ci + '{0}_diff{1}'.format(i + 1,ki)] = dci.loc[ki]['timestamp'] - dci.loc[ki+1]['timestamp']  # 距离上一次的登陆时间间隔
                    except:
                        res[ci + '{0}_diff{1}'.format(i + 1,ki)] = None

                res[ci + '_time_max{0}'.format(i)] = dci['timelong'].max()                               # ip 之前登陆的 timelong 最大
                res[ci + '_time_min{0}'.format(i)] = dci['timelong'].min()                               # ip 之前登陆的 timelong 最小
                res[ci + '_time_mean{0}'.format(i)] = dci['timelong'].mean()                             # ip 之前登陆的 timelong 均值
                res[ci + '_cnt{0}'.format(i)] = dci.shape[0]                                             # ip 之前登陆的次数
                res[ci + '_cnt_rate{0}'.format(i)] = 1.0 * dci[dci['result'] != 1].shape[0] / (1 + res[ci + '_cnt'])

                for tpi in [1,2,3]:
                    res[ci + 'type_{0}_{1}cnt'.format(i,tpi)] = dci[dci['type']==tpi].shape[0]

                for logi in [1,2,10,11]:
                    res[ci + 'log_{0}_{1}cnt'.format(i,logi)] = dci[dci['log_from']==logi].shape[0]

                for logi in [-2,-1,1,6,31]:
                    res[ci + 'result_{0}_{1}cnt'.format(i,logi)] = dci[dci['result']==logi].shape[0]

                for ii in ['id','ip','device','type','city']:
                    # TODO  ip,city 重复
                    if ii != ci:
                        res[ci + "_" + ii+"{0}".format(i)] = dci[ii].unique().size              # ip 之前登陆的 id 数
            except:
                for ki in [0, 1]:
                    res[ci + '{0}_diff{1}'.format(i + 1, ki)] = None
                res[ci + '_time_max{0}'.format(i)] = None
                res[ci + '_time_min{0}'.format(i)] = None
                res[ci + '_time_mean{0}'.format(i)] = None
                res[ci + '_cnt{0}'.format(i)] = 0
                res[ci + '_cnt_rate{0}'.format(i)] = 0

                for tpi in [1,2,3]:
                    res[ci + 'type_{0}_{1}cnt'.format(i,tpi)] = 0

                for logi in [1,2,10,11]:
                    res[ci + 'log_{0}_{1}cnt'.format(i,logi)] = 0

                for logi in [-2,-1,1,6,31]:
                    res[ci + 'result_{0}_{1}cnt'.format(i,logi)] = 0

                for ii in ['id','ip','device','type','city']:
                    # TODO  ip,city 重复
                    if ii != ci:
                        res[ci + "_" + ii+"{0}".format(i)] = 0             # ip 之前登陆的 id 数

        for ci in [('id', 'ip'), ('id', 'device'), ('id', 'type'),
                                   ('ip', 'device'), ('ip', 'type'), ('id', 'city')]:
            try:
                idx = login_data1.loc[0]['index']
                idata, jdata = login_data.loc[idx + i][ci[0]], login_data.loc[idx + i][ci[1]]

                dci = d[((d[ci[0]] == idata) & (d[ci[1]] == jdata))]

                dci = dci.sort_values('time', ascending=False) \
                    .reset_index(drop=True)
                cis = ci[0] + ci[1]
                for ki in [0, 1]:
                    try:
                        res[cis + '{0}_diff{1}'.format(i + 1, ki)] = dci.loc[ki]['timestamp'] - dci.loc[ki + 1]['timestamp']  # 距离上一次的登陆时间间隔
                    except:
                        res[cis + '{0}_diff{1}'.format(i + 1, ki)] = None

                res[cis + '_time_max'] = dci['timelong'].max()  # ip 之前登陆的 timelong 最大
                res[cis + '_time_min'] = dci['timelong'].min()  # ip 之前登陆的 timelong 最小
                res[cis + '_time_mean'] = dci['timelong'].mean()  # ip 之前登陆的 timelong 均值
                res[cis + '_cnt'] = dci.shape[0]  # ip 之前登陆的次数
                res[cis + '_cnt_rate'] = 1.0 * dci[dci['result'] != 1].shape[0] / (1 + res[cis + '_cnt'])

                for tpi in [1, 2, 3]:
                    res[cis + 'type_{0}_{1}cnt'.format(i, tpi)] = dci[dci['type'] == tpi].shape[0]

                for logi in [1, 2, 10, 11]:
                    res[cis + 'log_{0}_{1}cnt'.format(i, logi)] = dci[dci['log_from'] == logi].shape[0]

                for logi in [-2, -1, 1, 6, 31]:
                    res[cis + 'result_{0}_{1}cnt'.format(i, logi)] = dci[dci['result'] == logi].shape[0]

                for ii in ['id', 'ip', 'device', 'type', 'city']:
                    if ii not in cis:
                        res[cis + "_" + ii] = dci[ii].unique().size  # ip 之前登陆的 id 数
            except:
                cis = ci[0] + ci[1]
                for ki in [0, 1]:
                    res[cis + '{0}_diff{1}'.format(i + 1, ki)] = None
                res[cis + '_time_max{0}'.format(i)] = None
                res[cis + '_time_min{0}'.format(i)] = None
                res[cis + '_time_mean{0}'.format(i)] = None
                res[cis + '_cnt{0}'.format(i)] = 0
                res[cis + '_cnt_rate{0}'.format(i)] = 0

                for tpi in [1, 2, 3]:
                    res[cis + 'type_{0}_{1}cnt'.format(i, tpi)] = 0

                for logi in [1, 2, 10, 11]:
                    res[cis + 'log_{0}_{1}cnt'.format(i, logi)] = 0

                for logi in [-2, -1, 1, 6, 31]:
                    res[cis + 'result_{0}_{1}cnt'.format(i, logi)] = 0

                for ii in ['id', 'ip', 'device', 'type', 'city']:
                    # TODO  ip,city 重复
                    if ii != cis:
                        res[cis + "_" + ii + "{0}".format(i)] = 0  # ip 之前登陆的 id 数
    print res
    return res

#t_trade_list = np.array(t_trade[['rowkey','id','trade_stamp','is_risk','time']]).tolist()
dtt = t_trade[t_trade['time']>='2015-03-01 00:00:00']

t_trade_list = dtt.index.tolist()
del dtt
"""
for i in t_trade_list[:10]:
    baseline_1(i)
"""
# 如果最近登陆统计存在
last_f = '../datas/all_3_7'
if os.path.exists(last_f):
        data = pd.read_csv(last_f)
else:
    import time
    start_time = time.time()
    pool = Pool(8)
    d = pool.map(baseline_1,t_trade_list)
    pool.close()
    pool.join()
    print 'time : ', 1.0*(time.time() - start_time)/60
    data = pd.DataFrame(d)
    print(data.shape)
    data.to_csv(last_f,index=None)
