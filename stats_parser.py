import os
import re
import subprocess
import sys
import tempfile

COLUMNS = [
    'result (avg) [s]', '\'+-', 'result (median) [s]',
    'EXPLORATION_TIME', 'MINIBATCH_SIZE', 'TRANSITIONS_HISTORY_SIZE', 'CONSTANT_LEARNING_RATE',
    'START_LEARNING_RATE', 'FINAL_LEARNING_RATE', 'LEARNING_RATE_CHANGE_EPISODES',
    'NETWORK_ARCHITECTURE', 'ERROR_FUNC', 'UPDATE_RULE', 'DISCOUNT_FACTOR',
    'CLIP_DELTA', 'SWAP_NETWORKS_EVERY', 'FINAL_EPSILON_GREEDY',
    'USE_LASAGNE', 'EVALUATE_AGENT_EACH', 'EVALUATION_EPISODES', 'MULTI_AGENT',
    'simulator time [h]', 'real time [min]', 'dir'
]
PLOT_EXT = ['eps', 'svg', 'png']


def float_round(f, digits=4, multiply=1.0):
    return str(round(float(f) * multiply, digits))


def get_dirs():
    for d in os.listdir(sys.argv[-1]):
        l = {'dir': d}
        d_abs = os.path.abspath(os.path.join(sys.argv[-1], d))
        if not os.path.isdir(d_abs) or (len(sys.argv) > 2 and not d.startswith(sys.argv[-2])):
            continue
        yield (d, d_abs)


def parse_stats():
    print('\t'.join(COLUMNS))
    final_result = {}
    for d_name, d in get_dirs():
        l = {'dir': d_name}
        # print('Processing {}'.format(d))
        for i, line in enumerate(open(os.path.join(d, 'stats.txt'))):
            line = line.strip()
            # avg
            if i == 1:
                r = line.strip().split(':')[-1]
                result, plus_minus = re.search(r'([\d.]+) \(\+- ([\d.]+)\)', r).groups()
                l['result (avg) [s]'] = float_round(result)
                l['\'+-'] = float_round(plus_minus)
            elif i == 5:
                l['simulator time [h]'] = float_round(line.strip().split(':')[-1], digits=1)
            elif i == 2:
                l['result (median) [s]'] = float_round(line.strip().split(':')[-1])
            elif i == 6:
                l['real time [min]'] = float_round(line.strip().split(':')[-1], digits=1)
            else:
                s = line.split('=')
                if s[0] in COLUMNS:
                    l[s[0]] = s[1]
        if l.get('START_LEARNING_RATE') == l.get('FINAL_LEARNING_RATE') and l.get('START_LEARNING_RATE'):
            l['CONSTANT_LEARNING_RATE'] = l.pop('START_LEARNING_RATE')
            del l['FINAL_LEARNING_RATE']
        for c in COLUMNS:
            print('{}\t'.format(l.get(c, '-')), end="")
        print('')
        final_result[d_name] = l
    return final_result


def make_plots(stats):
    # eval every 500/1000 episodes
    with tempfile.NamedTemporaryFile('w') as f_eval_stats:
        print(f_eval_stats.name)
        i = 0
        params = []
        for d_name, d in get_dirs():
            params.append(d_name.split('___')[1:])

        important_params = []
        for i, p in enumerate(zip(*params)):
            if len(set(p)) != 1:
                important_params.append(i+1)

        # eval stats
        for d_name, d in get_dirs():
            i += 1
            header = []
            for p in important_params:
                header.append(d_name.split('___')[p])
            f_eval_stats.write('"{}"'.format(', '.join(header)).replace('_', '-') + '\n')
            for line in open(d + '/evaluation_stats2gnuplot.txt'):
                if not line.startswith('20000'):
                    f_eval_stats.write(line)
                else:
                    f_eval_stats.write('\t'.join(map(str, ('20000', '0', '0', stats[d_name]['result (avg) [s]'], stats[d_name]['result (median) [s]'], '0', stats[d_name]['\'+-'], '0', '0', '\n'))))
            f_eval_stats.write('\n\n')

        for metric, val, stdev in (('random', 5.3, 1.8), ('always-hold', 2.9, 1.0), ('hand-coded', 13.3, 8.3)):
            f_eval_stats.write(metric + '\n')
            for ep in (0, 20000):
                f_eval_stats.write('\t'.join(map(str, (ep, 0, 0, val, val, 0, stdev, 0, 0, '\n'))))
            f_eval_stats.write('\n\n')
        f_eval_stats.flush()
        options = {
            'max_x': "21000",
            'max_y': "22",
            'title': 'Graph',
            'x_title': 'Episodes count',
            'y_title': 'Episode Duration (seconds)',
            'terminal': 'svg',
            'file_stats': f_eval_stats.name,
            'series': i,
        }
        for exp in PLOT_EXT:
            additional_opts = {
                '1:5:5': {
                    'title': 'Median episode duration during evaluation (100 every 1000 episodes)',
                    'out_file': os.path.join(sys.argv[-1], 'eval_median.{}'.format(exp)),
                },
                '1:4:4': {
                    'title': 'Average episode duration during evaluation (100 every 1000 episodes)',
                    'out_file': os.path.join(sys.argv[-1], 'eval_avg.{}'.format(exp)),
                }
            }
            if exp == 'eps':
                exp = 'postscript eps enhanced color'
            for cols, add_opts in additional_opts.items():
                window_opts = options.copy()
                window_opts.update(add_opts)
                window_opts['cols'] = cols
                window_opts['terminal'] = exp
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools', 'batch_graph_eval.gnuplot.tmpl')) as graph_tmpl:
                    with tempfile.NamedTemporaryFile('w') as f_graph:
                        g = graph_tmpl.read().format(**window_opts)
                        f_graph.write(g)
                        f_graph.flush()
                        print(f_graph.name)
                        subprocess.call(['gnuplot', f_graph.name])

        # agent logs
        for d_name, d in get_dirs():
            i += 1
            header = []
            for p in important_params:
                header.append(d_name.split('___')[p])
            f_eval_stats.write('"{}"'.format(', '.join(header)).replace('_', '-') + '\n')
            for line in open(d + '/evaluation_stats2gnuplot.txt'):
                if not line.startswith('20000'):
                    f_eval_stats.write(line)
                else:
                    f_eval_stats.write('\t'.join(map(str, ('20000', '0', '0', stats[d_name]['result (avg) [s]'], stats[d_name]['result (median) [s]'], '0', stats[d_name]['\'+-'], '0', '0', '\n'))))
            f_eval_stats.write('\n\n')

stats = parse_stats()
make_plots(stats)
