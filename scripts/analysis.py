from numpy import *
from pickle import load
from os.path import join, isfile
from copy import deepcopy
from random import shuffle
from matplotlib import cm

from output import *

#-------------------------------------------------------------------------------
# CONFIG

#plt.rc('font', family='calibri')
#plt.rc('font', size=18)

#-------------------------------------------------------------------------------
# INPUT

#batch output directory
batchdir = join('..', 'results', 'batch-runs')

#grid directory
gdir = join('..', 'results', 'grid')

#specific gas constant for water (J/kg*K)
R_w = 461

#density of water (kg/m^3)
rho_w = 1e3

#latent heat of water (J/kg)
L_w = 24.93e5

#freezing point of water (K)
T_f_w = 273

#seconds in one Earth year
yrsec = 3600*24*365.25

#seconds in one hour
hrsec = 3600

#groundwater flow width, about half Gale's diameter (m)
L_lake = 75e3

#lake area
A_lake = 4e3*1e6

#-------------------------------------------------------------------------------
# FUNCTIONS

flatten = lambda L: [item for sublist in L for item in sublist]

#Clausius-Clapeyron for water
f_psat = lambda T: 611*exp(-(L_w/R_w)*(1/T - 1/T_f_w))

#potential evaporation/sublimation from
#Wordsworth, R. D., Kerber, L., Pierrehumbert, R. T., Forget, F. & Head, J. W. Comparison of “warm and wet” and “cold and icy” scenarios for early Mars in a 3-D climate model. Journal of Geophysical Research: Planets 120, 1201–1219 (2015).
f_Epot_m = lambda T: 2.75e-3*5*f_psat(T)/(R_w*T)

#convert mass per area*time from Epot to depth per area*time
f_Epot_d = lambda T: f_Epot_m(T)/rho_w

lake_evap = lambda F, L, A: F*L/A

lake_area = lambda F, L, E: F*L/E

def plot_transient_groups(stg, var, varname, varunit, fvar=lambda v: '%g' % v, ymin=None):

    cmap = cm.get_cmap('tab10')
    colors = [cmap(i) for i in (0,4,6,9)]

    #plot all trials split by permeability
    uv = sorted(stg[var].unique())
    fig, axs = plt.subplots(2,len(uv))
    fig.subplots_adjust(wspace=0.05, hspace=0.05)
    for j,v in enumerate(uv):
        sl = stg[stg[var] == v]
        for tdir in sl.index:
            E = Evap(tdir, gdir)
            s = read_settings(join(tdir, 'settings.txt'))
            if s['Rmax'] == 1:
                i = 0
            else:
                i = 1
            axs[i,j].semilogy(E.tf/(1e3*TU), E.evapf, color=colors[j], alpha=0.3)
        axs[0,j].set_title('%s = %s %s' % (varname, fvar(v), varunit))
    for i in range(2):
        for j in range(1,len(uv)):
            axs[i,j].set_yticklabels([])
            axs[i,j].tick_params(axis='y', length=0)
    for j in range(len(uv)):
        axs[0,j].set_xticklabels([])
        axs[0,j].tick_params(axis='x', length=0)
    faxs = flatten(axs)
    if ymin is None:
        ymin = min([ax.get_ylim()[0] for ax in faxs])
    ymax = max([ax.get_ylim()[1] for ax in faxs])
    for ax in faxs:
        ax.spines['top'].set_visible(True)
        ax.spines['right'].set_visible(True)
        ax.set_ylim(ymin, ymax)
    for i in range(2):
        ax = axs[i,-1].twinx()
        ax.set_yscale('log')
        ax.grid(False)
        ax.set_ylim(
            lake_evap(ymin, L_lake, A_lake)*hrsec*1e3,
            lake_evap(ymax, L_lake, A_lake)*hrsec*1e3
        )
    fig.text(0.95, 0.5, 'Balancing Evaporation Rate (mm/hr)\n4000 km$^2$ surface',
            va='center', ha='center', rotation=270)
    fig.text(0.5, 0.04, 'Time (1000 %s)' % TL, ha='center')
    fig.text(0.04, 0.5, 'Water Delivery (m$^2$/s)', va='center', rotation='vertical')
    #fig.text(0.95, 0.75, 'Maximum Recharge', va='center', rotation=270)
    #fig.text(0.95, 0.35, 'No Recharge', va='center', rotation=270)

    return(fig, ax)

def plot_snapshots(stg, var, cvar, times,
        varname='', varunit='', fvar=lambda v: '%g' % v,
        cvarname='', cvarunit='', fcvar=lambda v: '%g' % v):

    fig, axs = plt.subplots(1,len(times))
    fig.subplots_adjust(wspace=0.1, hspace=0.05)
    cm = plt.get_cmap('tab10')
    colors = [cm(i) for i in (0,4,6,9)]
    uv = array(sorted(stg[var].unique()))
    ucv = array(sorted(stg[cvar].unique()))
    csp = linspace(-0.075*len(ucv), 0.075*len(ucv), len(ucv))
    legh, legl = [], []
    for i,v in enumerate(uv):
        for j,t in enumerate(times):
            axs[j].set_yscale('log')
            for k,cv in enumerate(ucv):
                #for rmax in [0,1]:
                sl = stg[(stg[var] == v) & (stg[cvar] == cv)]
                #sl = sl[sl['Rmax'] == rmax]
                es = [Evap(tdir, gdir) for tdir in sl.index]
                e = array([interp(t, e.tf, e.evapf, right=nan) for e in es])
                e = e[~isnan(e)]
                x = array([i+csp[k]]*len(e))
                y = lake_evap(e, L_lake, A_lake)*hrsec*1e3
                if len(y) > 0:
                    #axs[j].scatter(x+0.1, y, s=2.5, c=colors[k])
                    r = axs[j].violinplot(y, positions=[x[0]])
                    r['bodies'][0].set_alpha(0)
                    for s in ['cmins', 'cmaxes', 'cbars']:
                        r[s].set_color(colors[k])
                        r[s].set_linewidth(1.5)
                if i == 0 and j == 0:
                    label = '%s = %s %s' % (cvarname, fcvar(cv), cvarunit)
                    legh.append(r['cbars'])
                    legl.append(label)

    ymin = min([ax.get_ylim()[0] for ax in axs])
    ymax = max([ax.get_ylim()[1] for ax in axs])
    for j in range(len(axs)):
        axs[j].set_ylim(ymin, ymax)
        axs[j].set_title('{:,g} {}'.format(times[j]/TU, TL))
        axs[j].grid(False, axis='x')
        axs[j].set_xticks(range(len(var)))
        axs[j].tick_params(axis='x', length=0)
        axs[j].set_xticklabels([fvar(v) for v in uv])
        axs[j].set_xlim(-0.2*len(uv), (len(uv)-1) + 0.2*len(uv))
        axs[j].spines['top'].set_visible(True)
        axs[j].spines['right'].set_visible(True)
        for i in range(len(uv) - 1):
            axs[j].plot([i+1/2]*2, [ymin,ymax], 'k', alpha=0.5)
    for j in range(1,len(axs)):
        axs[j].set_yticklabels([])
        axs[j].tick_params(axis='y', length=0)
    axs[0].set_ylabel('Balancing Evaporation Rate (mm/hr)\n4000 km$^2$ surface')
    fig.text(0.5, 0.04, '%s (%s)' % (varname, varunit), ha='center')
    axs[0].legend(legh, legl, loc='upper left')

#-------------------------------------------------------------------------------
# MAIN

#read the grid files
grid = Grid(gdir)
#read all settings files into DataFrame
stg = walk_settings(batchdir)
#read evaporation time series
evaps = {fn:Evap(fn, gdir) for fn in stg.index}

#sensitivity plots
pcols = ['kTr', 'Ts0', 'Tsf', 'TsLR'] #columns to plot variation in
vcols = ['kTr', 'Ts0', 'Tsf', 'TsLR', 'perm0', 'permgam', 'Rmax'] #columns that vary
plabe = dict(zip(pcols, [r'$\alpha_r$', '$T_{si}$', '$T_{sf}$', r'$\Gamma$']))
ranges = [{},{}]
for rmax in [0,1]:
    for i,pcol in enumerate(pcols):
        ranges[rmax][pcol] = []
        gcols = deepcopy(vcols) #columns to groupby
        gcols.remove(pcol)
        g = stg[stg['Rmax'] == rmax].groupby(gcols).groups
        for k in g:
            sl = stg.loc[g[k]].sort_values(pcol)
            es = [evaps[i] for i in sl.index]
            n = min([len(e.tf)-1 for e in es])
            ef = [e.evapf[n] for e in es]
            r = abs(max(ef)/min(ef))
            ranges[rmax][pcol].append(r)
for i in [0,1]:
    fig, axs = plt.subplots(2,2)
    axs = flatten(axs)
    mx = max([max(ranges[i][k]) for k in ranges[i]])
    bins = linspace(0, mx, 21)
    for j,k in enumerate(pcols):
        axs[j].hist(ranges[i][k], bins=bins, color='gray')
        axs[j].set_title(plabe[k])
    if i == 0:
        fig.suptitle('Without Recharge')
    else:
        fig.suptitle('With Recharge')
    fig.text(0.5, 0.04, 'Max Groundwater Flow/Min Groundwater Flow\nVarying a Single Parameter', ha='center')
    fig.tight_layout()

#plot all trials split by permeability
#fig, axs = plot_transient_groups(stg[stg['Ts0'] == 220], 'perm0', '$k_0$', 'm$^2$', lambda v: '10$^{%g}$' % log10(v))

#plot all trials split by final temperature
#fig, axs = plot_transient_groups(stg, 'Tsf', 'T$_{sf}$', 'K')

#plot all trials split by initial temperature
#fig, axs = plot_transient_groups(stg, 'Ts0', 'T$_{si}$', 'K')

#plot all trials split by lapse rate
#fig, axs = plot_transient_groups(stg, 'TsLR', r'$\Gamma$', 'K/km', lambda v: '%g' % (v*1e3))

#plot all trials split by conductivity
#fig, axs = plot_transient_groups(stg, 'kTr', r'$\alpha$', r'W/m\cdot K', lambda v: '%g' % (v*1e3))

#plot a temperature evolution example
params = dict(
    Rmax=0,
    TsLR=0.0025,
    Ts0=250,
    Tsf=285,
    kTr=1
)
for k in evaps:
    e = evaps[k]
    if all([isclose(stg.at[k,p], params[p]) for p in params]):
        plot_temperature(Trial(k, gdir), grid, Tlim=inf)
        break

sl = stg[(stg['kTr'] == 2)]# & (isclose(stg['perm0'], 1e-12) | isclose(stg['perm0'], 1e-13))]
sl = stg[(stg['perm0'] > 2e-14) & (stg['Rmax'] == 0)]
plot_snapshots(sl, 'perm0', 'Tsf', [i*1e3*yrsec for i in (1,10,25)],
        'Surface Permeability $k_0$', 'm$^2$', lambda v: '10$^{%g}$' % log10(v),
        'T$_{sf}$', 'K', lambda v: '%g' % v)

#plot_snapshots(sl, 'Tsf', 'perm0', [i*1e3*yrsec for i in (1,10,20)],
#        '$T_{sf}$', 'K', lambda v: '%g' % v,
#        '$k_0$', 'm$^2$', lambda v: '10$^{%g}$' % log10(v))

#plot_snapshots(sl, 'Ts0', 'Tsf', [i*1e3*yrsec for i in (1,10,20)],
#        '$T_{si}$', 'K', lambda v: '%g' % v,
#        '$T_{sf}$', 'K', lambda v: '%g' % v,)

plt.show()
