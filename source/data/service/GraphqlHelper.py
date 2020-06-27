# coding=gbk
from source.utils.StringKeyUtils import StringKeyUtils
import json


class GraphqlHelper:
    """����graphql ��Ҫ��query���"""

    @staticmethod
    def getTimeLineQueryByNodes(body):
        """���ز�ѯtimeline��Ҫ�����"""
        body[StringKeyUtils.STR_KEY_QUERY] = GraphqlHelper.STR_KEY_QUERY_PR_TIMELINE
        return body

    @staticmethod
    def getGraphqlVariables(body, args=None):
        """���ش��ݲ�����Ҫ��json"""
        if args is None or isinstance(body, dict) is False:
            body[StringKeyUtils.STR_KEY_VARIABLES] = GraphqlHelper.STR_KEY_NONE
        else:
            body[StringKeyUtils.STR_KEY_VARIABLES] = json.dumps(args)
        return body

    # @staticmethod
    # def getGraphqlArg(args=None):
    #     """���ش��ݲ�����Ҫ��json"""
    #     pass

    STR_KEY_QUERY_VIEWER = "{viewer{name}}"

    STR_KEY_NONE = "{}"

    STR_KEY_QUERY_PR_TIMELINE = '''
 query($id:ID!) { 
  node(id:$id) {
    ... on PullRequest {
      id
      author {
        login
      }
      timelineItems(first:100) {
        edges {
          node {
            __typename
            ... on Node {
               id
            }
              
            ... on PullRequestCommit {
              commit {
                oid
              }
            }
            
            ... on PullRequestReview {
              commit {
                oid
              }
              author {
                login
              }
              comments(first: 100) {
                nodes {
                  commit {
                    oid
                  }
                  originalCommit {
                    oid
                  }
                  author {
                    login
                  }
                  path
                }
              }
            }
            ... on HeadRefForcePushedEvent {
              afterCommit {
                oid
              }
              beforeCommit {
                oid
              }
            }
            ... on PullRequestReviewThread {
              id
              comments(first: 100) {
                nodes {
                  commit {
                    oid
                  }
                  originalCommit {
                    oid
                  }
                  author {
                    login
                  }
                  path
                }
              }
            }
            ... on MergedEvent {
              id
              commit {
                oid
              }
            }
            ... on IssueComment {
              author {
                login
              }
            }
          }   
        }
        }
      }
    }
  rateLimit {
    limit
    cost
    remaining
    resetAt
  }
}
    '''
